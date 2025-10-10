# Contributing to FranklinWH Integration

First off, thank you for considering contributing to the FranklinWH integration! 🎉

## Code of Conduct

Please be respectful and constructive in your interactions with other contributors.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates.

When reporting a bug, include:
- **Home Assistant version**
- **Integration version**
- **Diagnostic data** (from Settings → Devices & Services → FranklinWH → Download Diagnostics)
- **Relevant log entries** (from Settings → System → Logs)
- **Steps to reproduce**
- **Expected vs actual behavior**

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:
- Use a clear and descriptive title
- Provide detailed description of the enhancement
- Explain why this would be useful
- Include examples if possible

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test thoroughly**
5. **Commit with clear messages** (`git commit -m 'Add amazing feature'`)
6. **Push to your fork** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Home Assistant development environment
- Git

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/richo/homeassistant-franklinwh.git
cd homeassistant-franklinwh
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up Home Assistant dev environment:
   - Use VS Code with Dev Containers extension (recommended)
   - Or set up a local Home Assistant development instance

### Testing

Before submitting a PR:

1. **Test your changes** in a real Home Assistant instance
2. **Check for linting errors**:
   ```bash
   pylint custom_components/franklin_wh/
   ```
3. **Verify no breaking changes** for existing users
4. **Test config flow** if you modified configuration
5. **Test entity creation** and updates
6. **Test switch controls** if applicable

### Code Style

- Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use type hints where possible
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Use meaningful variable names

### Commit Messages

- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs liberally

Examples:
```
Add support for battery reserve control
Fix entity ID typo in sensor platform
Update documentation for config flow
```

## Project Structure

```
custom_components/franklin_wh/
├── __init__.py           # Integration setup and services
├── config_flow.py        # UI configuration flow
├── const.py              # Constants
├── coordinator.py        # Data update coordinator
├── diagnostics.py        # Diagnostics support
├── manifest.json         # Integration metadata
├── sensor.py             # Sensor entities
├── switch.py             # Switch entities
├── services.yaml         # Service definitions
├── strings.json          # UI strings
└── translations/
    └── en.json          # English translations
```

## Adding New Features

### Adding a New Sensor

1. Add sensor description to `SENSOR_TYPES` in `sensor.py`
2. Add value function to extract data from coordinator
3. Test the sensor in Home Assistant
4. Update README.md with new sensor documentation

Example:
```python
FranklinWHSensorEntityDescription(
    key="new_sensor",
    name="New Sensor Name",
    native_unit_of_measurement=UnitOfPower.WATT,
    device_class=SensorDeviceClass.POWER,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda data: data.stats.current.new_value if data.stats else None,
),
```

### Adding a New Service

1. Define service in `const.py`
2. Add service schema in `services.yaml`
3. Implement handler in `__init__.py`
4. Add method to `coordinator.py`
5. Add translations to `strings.json`
6. Document in README.md

### Improving Local API Support

The local API is experimental. To improve it:

1. Research FranklinWH local communication protocols
2. Test with actual hardware if possible
3. Update `coordinator.py` to handle local API calls
4. Add configuration options if needed
5. Document findings and limitations

## API Library Development

This integration depends on the [`franklinwh-python`](https://github.com/richo/franklinwh-python) library.

If you need features not in the library:
1. Submit a PR to `franklinwh-python` first
2. Update the version requirement in `manifest.json`
3. Then implement the integration feature

## Documentation

When adding features, update:
- `README.md` - User-facing documentation
- `MIGRATION.md` - If there are breaking changes
- `strings.json` - UI text and translations
- Inline code comments - For complex logic

## Release Process

Maintainers will handle releases, but for reference:

1. Update version in `manifest.json`
2. Update `README.md` changelog
3. Create a git tag
4. Push to GitHub
5. Create a release with notes

## Questions?

- Open a [GitHub Discussion](https://github.com/richo/homeassistant-franklinwh/discussions)
- Check existing [Issues](https://github.com/richo/homeassistant-franklinwh/issues)
- Review the [README](README.md)

## License

By contributing, you agree that your contributions will be licensed under the same licenses as the project (MIT and Apache 2.0).

---

Thank you for contributing! 🙏

