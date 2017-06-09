# SublimePhpArrayConverter

A Sublime Text 3 packages which converts PHP array syntax to brackets.

![ScreenShot](https://raw.github.com/gh640/SublimePhpArrayConverter/master/assets/screenshot.gif)


## Dependencies

This packages uses `php` command.


## Installation

1. Download the zip file file: https://github.com/gh640/SublimePhpArrayConverter/archive/master.zip
2. Unzip the archive, rename the 'SublimePhpArrayConverter' folder to 'PhpArrayConverter' and move it into your Sublime Text 'Packages' directory.


## Usage

### Commands

Run the plugin from the command palette:

1. Open the command palette (ctrl/cmd + shift + p).
2. Select 'PhpArrayConverter: Convert array'.

### Settings

The default settings are set as below.

```json
{
  "auto_convert_on_save": false,
  "path": ""
}
```

These values can be overwritten through `Preferences` - `Package settings` - `PhpArrayConverter` - `Settings - User`.

- `auto_convert_on_save` is a setting to turn on/off the auto conversion function. The default value is `false` and the auto conversion function is disabled. If you want to enable the auto conversion, set this to `true` in your setting file.
- `path` is a value which is converted to the environment variable `$PATH` when `php` command to tokenize the php code is run. Change this value to specify which `php` should be used in your environment.

## License

Licensed under the MIT license.
