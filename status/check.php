<?php

$BOT_TOKEN = '8824530584:AAGMq0CDiSMoHgBuPun94vB5Iqbj8NoP9D0';
$CHANNEL   = '@zotusvpn_status';
$SUB_FILE  = __DIR__ . '/../../sub.txt';
$STATE_FILE = __DIR__ . '/state.json';
$LOG_FILE  = __DIR__ . '/log.txt';
$TIMEOUT   = 15;
$POST_TTL  = 3600; // 1 час

// ═══════════════════════════════════════════════════════════════════════════

function logMessage(string $message): void {
    $timestamp = date('Y-m-d H:i:s');
    file_put_contents($GLOBALS['LOG_FILE'], "[{$timestamp}] {$message}\n", FILE_APPEND);
}

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

function buildDownMessage(string $name): array {
    // Plain text for offset calculation (UTF-16 code units)
    $prefix1 = "❗️ Сервер «{$name}\" временно недоступен\n\n";
    $prefix2 = $prefix1 . "✅ В ближайшее время его работа восстановится\n";
    $prefix3 = $prefix2 . "⌛️ пост будет удален в течении часа\n\n";

    $text = "❗️ Сервер «{$name}\" временно недоступен\n\n";
    $text .= "✅ В ближайшее время его работа восстановится\n";
    $text .= "⌛️ пост будет удален в течении часа\n\n";
    $text .= "🟢 Zotus VPN. Статус (http://t.me/zotusvpn_status)";

    // Offsets in UTF-16 code units for custom emoji entities
    // ❗️ at offset 0
    // ✅ at start of line 2 (after prefix1)
    // ⌛️ at start of line 3 (after prefix2)
    // 🟢 at start of line 4 (after prefix1 + "✅ В ближайшее время его работа восстановится\n⌛️ пост будет удален в течении часа\n\n")

    $entities = [
        ['type' => 'custom_emoji', 'offset' => 0, 'length' => 1, 'custom_emoji_id' => '5220197908342648622'],
        ['type' => 'custom_emoji', 'offset' => mb_strlen($prefix1, 'UTF-16'), 'length' => 1, 'custom_emoji_id' => '5219899949281453881'],
        ['type' => 'custom_emoji', 'offset' => mb_strlen($prefix2, 'UTF-16'), 'length' => 1, 'custom_emoji_id' => '5891211339170326418'],
        ['type' => 'custom_emoji', 'offset' => mb_strlen("❗️ Сервер «{$name}\" временно недоступен\n\n✅ В ближайшее время его работа восстановится\n⌛️ пост будет удален в течении часа\n\n", 'UTF-16'), 'length' => 1, 'custom_emoji_id' => '5416081784641168838'],
    ];

    $text = "❗️ Сервер «{$name}\" временно недоступен\n\n✅ В ближайшее время его работа восстановится\n⌛️ пост будет удален в течении часа\n\n🟢 Zotus VPN. Статус (http://t.me/zotusvpn_status)";

    return ['text' => $text, 'entities' => $entities];
}

function sendPost(string $text, array $entities = []): ?array {
    return tg('sendMessage', [
        'chat_id' => $GLOBALS['CHANNEL'],
        'text' => $text,
        'parse_mode' => 'HTML',
        'entities' => $entities,
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

function logMessage(string $message): void {
    $timestamp = date('Y-m-d H:i:s');
    file_put_contents($GLOBALS['LOG_FILE'], "[{$timestamp}] {$message}\n", FILE_APPEND);
}

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

function sendPost(string $text, array $entities = []): ?array {
    return tg('sendMessage', [
        'chat_id' => $GLOBALS['CHANNEL'],
        'text' => $text,
        'parse_mode' => 'HTML',
        'entities' => $entities,
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

// ═══════════════════════════════════════════════════════════════════════════

// Парсим sub.txt
if (!file_exists($SUB_FILE)) {
    $msg = "sub.txt not found: $SUB_FILE";
    logMessage("ERROR: $msg");
    die($msg . "\n");
}
$lines = file($SUB_FILE, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
$servers = [];

foreach ($lines as $line) {
    $line = trim($line);
    if (!$line || $line[0] === '#') continue;

    // Парсим VLESS URL: vless://uuid@host:port?params#name
    if (!preg_match('~^vless://[^@]+@([^:]+):(\d+)\?(.+?)(?:#(.+))?$~', $line, $m)) continue;

    $host   = $m[1];
    $port   = (int)$m[2];
    $params = $m[3];
    $rawName= $m[4] ?? "$host:$port";

    // Декодируем имя
    $name = rawurldecode($rawName);
    $name = str_replace(['?PLUS', '+PLUS'], '', $name);
    $name = trim($name);
    if (!$name) $name = "$host:$port";

    // Извлекаем SNI
    $sni = $host;
    if (preg_match('/sni=([^&]+)/', $params, $sm)) {
        $sni = rawurldecode($sm[1]);
    }

    // Извлекаем security
    $security = '';
    if (preg_match('/security=([^&]+)/', $params, $sm)) {
        $security = rawurldecode($sm[1]);
    }

    $servers[] = [
        'id'   => md5($host . ':' . $port),
        'host' => $host,
        'port' => $port,
        'name' => $name,
        'sni'  => $sni,
        'security' => $security,
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
        if ($currentEntry) {
            if (($currentEntry['msg_id'] ?? 0) > 0) {
                deletePost($currentEntry['msg_id']);
            }
            unset($state[$id]);
            $anyChange = true;
            echo "RECOVERED: {$srv['name']} ({$srv['host']}:{$srv['port']})\n";
        }
    } else {
        if ($currentEntry) {
            $age = $now - ($currentEntry['down_since'] ?? $now);
            if ($age >= $POST_TTL) {
                if (($currentEntry['msg_id'] ?? 0) > 0) {
                    deletePost($currentEntry['msg_id']);
                }
                $msgData = buildDownMessage($srv['name']);
                $result = sendPost($msgData['text'], $msgData['entities']);
                $msgId = $result['result']['message_id'] ?? 0;
                $state[$id] = ['down_since' => $now, 'msg_id' => $msgId];
                $anyChange = true;
                echo "REPOSTED (1h): {$srv['name']} — msg #{$msgId}\n";
            }
        } else {
            $msgData = buildDownMessage($srv['name']);
            $result = sendPost($msgData['text'], $msgData['entities']);
            $msgId = $result['result']['message_id'] ?? 0;
            $state[$id] = ['down_since' => $now, 'msg_id' => $msgId];
            $anyChange = true;
            echo "DOWN: {$srv['name']} ({$srv['host']}:{$srv['port']}) — msg #{$msgId}\n";
        }
    }
}

if ($anyChange) {
    file_put_contents($STATE_FILE, json_encode($state, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
}

echo "Done. " . count($state) . " servers down.\n";

// ═══════════════════════════════════════════════════════════════════════════

function checkServer(array $srv): bool {
    global $TIMEOUT;
    $host = $srv['host'];
    $port = (int)$srv['port'];
    $security = $srv['security'] ?? '';

    // TLS-проверка (reality / tls)
    if ($security === 'reality' || $security === 'tls') {
        $hostEsc = escapeshellarg($host);
        $sniEsc  = escapeshellarg($srv['sni']);
        $cmd = "timeout {$TIMEOUT} openssl s_client -connect {$host}:{$port} -servername {$sniEsc} </dev/null 2>/dev/null";

        exec($cmd, $output, $exitCode);
        if ($exitCode === 0 && strpos(implode("\n", $output), 'CONNECTED') !== false) {
            return true;
        }
        if ($exitCode === 124) {
            exec($cmd, $output, $exitCode);
            if ($exitCode === 0 && strpos(implode("\n", $output), 'CONNECTED') !== false) {
                return true;
            }
        }
        return false;
    }

    // Простой TCP (ws без TLS, xhttp, grpc без TLS)
    $errno = 0; $errstr = '';
    $fp = @fsockopen($host, $port, $errno, $errstr, $TIMEOUT);
    if ($fp) {
        fclose($fp);
        return true;
    }
    if ($errno === 110) {
        $fp = @fsockopen($host, $port, $errno, $errstr, $TIMEOUT);
        if ($fp) { fclose($fp); return true; }
    }
    return false;
}