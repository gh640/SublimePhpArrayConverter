<?php

main();

/**
 * Main function.
 */
function main() {
    $code = get_code_from_stdin();
    // list($filename, $code) = get_code_from_file();
    $tokens = token_get_all($code);
    $tokens_replaced = replace_tokens($tokens);

    $retval = array(
      // 'file' => $filename,
      'tokens' => $tokens_replaced,
    );

    print json_encode($retval);
}

/**
 * Helper function: get code from stdin.
 */
function get_code_from_stdin() {
    return file_get_contents('php://stdin');
}

/**
 * Helper function: get php code from a file.
 */
function get_code_from_file() {
    global $argv;

    if (count($argv) !== 2) {
        quit('No file name is passed.');
    }

    $filename = $argv[1];
    $code = file_get_contents($filename);

    if ($code === false) {
        quit('File cannot be read.');
    }

    return array($filename, $code);
}

/**
 * Helper function: replace token values.
 *
 * @param array $tokens
 *   A list of tokens returned by token_get_all().
 */
function replace_tokens($tokens) {
    $tokens_replaced = array();
    foreach ($tokens as $token) {
        $token_replaced = $token;
        if (is_array($token)) {
            $token_replaced[0] = map_token($token_replaced[0]);
        }

        $tokens_replaced[] = $token_replaced;
    }

    return $tokens_replaced;
}

/**
 * Helper function: map a token value.
 *
 * This is necessary for python script to process the tokens since values for
 * token contants changes.
 *
 * @param int $token
 *   Token value.
 */
function map_token($token) {
    $map = array(
        T_OPEN_TAG => 'T_OPEN_TAG',
        T_ARRAY => 'T_ARRAY',
        T_WHITESPACE => 'T_WHITESPACE',
    );

    return isset($map[$token]) ? $map[$token] : $token;
}

/**
 * Helper function: print error and exit.
 */
function quit($message) {
    file_put_contents('php://stderr', $message . PHP_EOL);
    exit(1);
}
