# SiteSage Installation Guide

## Requirements

### Python Environment

- Python 3.9+ (tested on 3.12)
- pip or uv package manager

### API Keys

#### Required

- **OpenAI API Key**: For LLM agents
  - Get from: https://platform.openai.com/api-keys
  - Set as: `OPENAI_API_KEY`

#### Map Services (Choose based on region)

**For US/Western Locations:**

- **Google Maps Platform API Key**
  - Get from: https://console.cloud.google.com/google/maps-apis
  - Enable the following APIs:
    - Geocoding API
    - Places API (New)
    - Distance Matrix API
    - Maps Static API
  - Set as: `GOOGLE_MAPS_API_KEY` or `GOOGLE_API_KEY`
  - **Important**: Billing must be enabled (even for free tier usage)

**For Chinese Locations:**

- **AMap (高德地图) API Key**
  - Get from: https://console.amap.com/
  - Set as: `AMAP_API_KEY` or `AMAP_KEY`
  - See [AMAP_API.md](AMAP_API.md) for details

### Data Sources

- **WorldPop Rasters**: Population and demographics data
  - Global coverage for population statistics
  - Configured in `src/tools/demographics_rt.py`

---

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Granine/SiteSage
cd SiteSage
```

### 2. Install Dependencies

Using pip:

```bash
pip install -e .
```

Using uv (recommended):

```bash
uv pip install -e .
```

The project will install the following dependencies (see `pyproject.toml`):

- railtracks (LLM orchestration)
- fastapi & uvicorn (web server)
- openai (OpenAI API client)
- ddgs (DuckDuckGo search)
- rasterio (geospatial data)
- numpy, pandas (data processing)

### 3. Configure Environment Variables

Copy the sample environment file:

```bash
cp .env.sample .env
```

Edit `.env` and add your API keys:

```bash
OPENAI_API_KEY=sk-...
GOOGLE_MAPS_API_KEY=AIza...  # For Western locations
# OR
AMAP_API_KEY=...  # For Chinese locations
```

**Note for Windows PowerShell users:**

```powershell
Copy-Item .env.sample .env
```

### 4. Verify Installation

Run a quick test:

```bash
cd src
python -c "import sitesage_backend; print('Backend loaded successfully')"
python -c "import sitesage_frontend; print('Frontend loaded successfully')"
```

---

## Platform-Specific Notes

### Windows

- Use PowerShell or Command Prompt
- Python might be invoked as `python` or `py`
- Virtual environment activation: `.venv\Scripts\Activate.ps1` (PowerShell) or `.venv\Scripts\activate.bat` (CMD)

### Linux/macOS

- Use bash or zsh
- Virtual environment activation: `source .venv/bin/activate`
- Ensure Python 3.9+ is available: `python3 --version`

### Environment Variables

**Linux/macOS:**

```bash
export OPENAI_API_KEY="your-key"
export GOOGLE_MAPS_API_KEY="your-key"
```

**Windows PowerShell:**

```powershell
$env:OPENAI_API_KEY="your-key"
$env:GOOGLE_MAPS_API_KEY="your-key"
```

**Windows CMD:**

```cmd
set OPENAI_API_KEY=your-key
set GOOGLE_MAPS_API_KEY=your-key
```

---

## Troubleshooting

### Import Errors

- Ensure you're in the correct directory (`src/`)
- Verify dependencies are installed: `pip list`
- Check Python version: `python --version`

### API Key Issues

- Verify `.env` file exists in `src/` directory
- Check environment variables are loaded: `python -c "import os, dotenv; dotenv.load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"`
- Ensure no quotes around values in `.env` file

### Missing Dependencies

- Reinstall: `pip install -e . --force-reinstall`
- Clear cache: `pip cache purge`

### WorldPop Data Issues

- Verify raster files are accessible
- Check paths in `src/tools/demographics.py`
- Ensure proper file permissions

---

## Next Steps

Once installed:

1. Review [DESIGN.md](DESIGN.md) for architecture details
2. See [API.md](API.md) for API reference
3. Check [../README.md](../README.md) for usage examples
4. Run the application following the Quick Start guide

---

## Development Setup

For development with testing:

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
pyright
```

See `pyproject.toml` for development configuration.
