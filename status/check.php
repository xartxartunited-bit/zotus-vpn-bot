<?php
/**
 * Zotus VPN Status Checker
 * Проверяет серверы из sub.txt через openssl s_client (TLS-хендшейк)
 * При падении шлёт пост в @zotusvpn_status, через час удаляет.
 * Запуск в кроне: */5 * * * * php /path/to/bot/status/check.php
 */

$BOT_TOKEN = '8824530584:AAGMq0CDiSMoHgBuPun94vB5Iqbj8NoP9D0';
$CHANNEL   = '@zotusvpn_status';
$SUB_FILE  = __DIR__ . '/../../sub.txt';
$STATE_FILE = __DIR__ . '/state.json';
$TIMEOUT   = 15;
$POST_TTL  = 3600; // 1 час

// ═══════════════════════════════════════════════════════════════════════════

function tg(string $method, array $data = []): ?array {
    global $BOT_TOKEN;
    $url = "https://api.telegram.org/bot{$BOT_TOKEN}/{$method}";
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER => ['Content-Type: application/json'],
        CURLOPT_POSTFIELDS => json_encode($data),
        CURLOPT_TIMEOUT => 10,
    ]);
    $r = curl_exec($ch);
    curl_close($ch);
    return json_decode($r, true);
}

function sendPost(string $text): ?array {
    return tg('sendMessage', [
        'chat_id' => $GLOBALS['CHANNEL'],
        'text' => $text,
        'disable_web_page_preview' => true,
    ]);
}

function deletePost(int $messageId): void {
    tg('deleteMessage', [
        'chat_id' => $GLOBALS['CHANNEL'],
        'message_id' => $messageId,
    ]);
}

// ═══════════════════════════════════════════════════════════════════════════

// Парсим sub.txt
if (!file_exists($SUB_FILE)) {
    die("sub.txt not found: $SUB_FILE\n");
}
$lines = file($SUB_FILE, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
$servers = [];

foreach ($lines as $line) {
    $line = trim($line);
    if (!$line || $line[0] === '#') continue;

    // Парсим VLESS URL: vless://uuid@host:port?params#name
    if (!preg_match('#^vless://[^@]+@([^:]+):(\d+)\?(.+?)(?:#(.+))?$#', $line, $m)) continue;

    $host   = $m[1];
    $port   = (int)$m[2];
    $params = $m[3];
    $rawName= $m[4] ?? "$host:$port";

    // Декодируем имя
    $name = rawurldecode($rawName);
    // Убираем ?PLUS и +PLUS из имени
    $name = str_replace(['?PLUS', '+PLUS'], '', $name);
    $name = trim($name);
    if (!$name) $name = "$host:$port";

    // Извлекаем SNI (если есть)
    $sni = $host;
    if (preg_match('/sni=([^&]+)/', $params, $sm)) {
        $sni = rawurldecode($sm[1]);
    }

    $servers[] = [
        'id'   => md5($host . ':' . $port),
        'host' => $host,
        'port' => $port,
        'name' => $name,
        'sni'  => $sni,
    ];
}

// ═══════════════════════════════════════════════════════════════════════════

// Загружаем состояние
$state = file_exists($STATE_FILE) ? json_decode(file_get_contents($STATE_FILE), true) : [];
if (!is_array($state)) $state = [];

$now = time();
$anyChange = false;

foreach ($servers as $srv) {
    $id = $srv['id'];
    $isUp = checkServer($srv);

    $currentEntry = $state[$id] ?? null;

    if ($isUp) {
        // Сервер жив
        if ($currentEntry) {
            // Был down → удаляем пост и убираем из стейта
            if (($currentEntry['msg_id'] ?? 0) > 0) {
                deletePost($currentEntry['msg_id']);
            }
            unset($state[$id]);
            $anyChange = true;
            echo "RECOVERED: {$srv['name']} ({$srv['host']}:{$srv['port']})\n";
        }
    } else {
        // Сервер упал
        if ($currentEntry) {
            // Уже в дауне — проверяем не пора ли перепостить (старше часа)
            $age = $now - ($currentEntry['down_since'] ?? $now);
            if ($age >= $POST_TTL) {
                // Удаляем старый пост
                if (($currentEntry['msg_id'] ?? 0) > 0) {
                    deletePost($currentEntry['msg_id']);
                }
                // Постим новый
                $msg = buildDownMessage($srv);
                $result = sendPost($msg);
                $msgId = $result['result']['message_id'] ?? 0;
                $state[$id] = ['down_since' => $now, 'msg_id' => $msgId];
                $anyChange = true;
                echo "REPOSTED (1h): {$srv['name']} — msg #{$msgId}\n";
            }
        } else {
            // Новый даун → пост
            $msg = buildDownMessage($srv);
            $result = sendPost($msg);
            $msgId = $result['result']['message_id'] ?? 0;
            $state[$id] = ['down_since' => $now, 'msg_id' => $msgId];
            $anyChange = true;
            echo "DOWN: {$srv['name']} ({$srv['host']}:{$srv['port']}) — msg #{$msgId}\n";
        }
    }
}

// Сохраняем состояние если были изменения
if ($anyChange) {
    file_put_contents($STATE_FILE, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

echo "Done. " . count($state) . " servers down.\n";

// ═══════════════════════════════════════════════════════════════════════════

function checkServer(array $srv): bool {
    global $TIMEOUT;
    $host = escapeshellarg($srv['host']);
    $port = (int)$srv['port'];
    $sni  = escapeshellarg($srv['sni']);

    // Первая попытка
    $cmd = "timeout {$TIMEOUT} openssl s_client -connect {$host}:{$port} -servername {$sni} </dev/null 2>/dev/null";
    exec($cmd, $output, $exitCode);

    if ($exitCode === 0) {
        // Ищем CONNECTED в выводе (успешный TLS)
        $out = implode("\n", $output);
        if (strpos($out, 'CONNECTED') !== false) {
            return true;
        }
    }

    // Вторая попытка (мгновенная) — таймаут = был таймаут
    if ($exitCode === 124) {
        exec($cmd, $output, $exitCode);
        if ($exitCode === 0) {
            $out = implode("\n", $output);
            if (strpos($out, 'CONNECTED') !== false) {
                return true;
            }
        }
    }

    return false;
}

function buildDownMessage(array $srv): string {
    $name = $srv['name'];
    return "❗ Сервер «{$name}» временно недоступен\n\n✅ В ближайшее время его работа восстановится\n⌛️ пост будет удален в течении часа\n\n🟢 Zotus VPN. Статус (http://t.me/zotusvpn_status)";
}
