# SiteSage Troubleshooting Guide

This guide covers common issues and their solutions when running SiteSage.

## Table of Contents

- [Installation Issues](#installation-issues)
- [API Key Issues](#api-key-issues)
- [Runtime Errors](#runtime-errors)
- [Map and Data Issues](#map-and-data-issues)
- [Performance Issues](#performance-issues)
- [UI/Frontend Issues](#ui-frontend-issues)

---

## Installation Issues

### Package Installation Fails

**Problem:** `pip install -e .` fails with dependency conflicts

**Solutions:**

1. Upgrade pip:

   ```bash
   python -m pip install --upgrade pip
   ```

2. Use a virtual environment:

   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\Activate.ps1
   # Linux/macOS
   source .venv/bin/activate

   pip install -e .
   ```

3. Install dependencies individually if conflicts persist:
   ```bash
   pip install railtracks fastapi uvicorn openai ddgs rasterio numpy pandas
   ```

### Import Errors

**Problem:** `ModuleNotFoundError` when running the application

**Solutions:**

1. Ensure you're in the correct directory:

   ```bash
   cd src
   python sitesage_frontend.py
   ```

2. Verify installation:

   ```bash
   pip list | grep sitesage
   ```

3. Reinstall in development mode:
   ```bash
   pip install -e . --force-reinstall --no-cache-dir
   ```

### Python Version Issues

**Problem:** `SyntaxError` or incompatibility errors

**Solution:** Verify Python version is 3.9 or higher:

```bash
python --version
# Should show Python 3.9.x or higher
```

If multiple Python versions are installed:

```bash
# Use specific version
python3.12 -m pip install -e .
python3.12 sitesage_frontend.py
```

---

## API Key Issues

### OpenAI API Key Not Found

**Problem:** `Error: OPENAI_API_KEY not set` or authentication failures

**Solutions:**

1. Check `.env` file exists in `src/` directory:

   ```bash
   ls src/.env  # Linux/macOS
   dir src\.env  # Windows
   ```

2. Verify `.env` file contents:

   ```
   OPENAI_API_KEY=sk-your-actual-key-here
   ```

   (No quotes around the value)

3. Test environment variable loading:

   ```bash
   cd src
   python -c "import os; import dotenv; dotenv.load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
   ```

4. Alternative: Set as system environment variable:

   ```bash
   # Linux/macOS
   export OPENAI_API_KEY="sk-your-key"

   # Windows PowerShell
   $env:OPENAI_API_KEY="sk-your-key"
   ```

### Google Maps API Errors

**Problem:** Geocoding fails or "API key invalid" errors

**Solutions:**

1. Verify API key in `.env`:

   ```
   GOOGLE_MAPS_API_KEY=AIzaSy...
   ```

2. Check required APIs are enabled in Google Cloud Console:

   - Geocoding API
   - Places API (New)
   - Distance Matrix API
   - Maps Static API

3. Verify billing is enabled (Google Maps requires billing account)

4. Check API key restrictions don't block your IP/application

5. Test API key:
   ```bash
   curl "https://maps.googleapis.com/maps/api/geocode/json?address=1600+Amphitheatre+Parkway,+Mountain+View,+CA&key=YOUR_KEY"
   ```

See [docs/INSTALLATION.md](INSTALLATION.md) for detailed Google Maps setup.

### AMap API Errors

**Problem:** Location search fails for Chinese addresses

**Solutions:**

1. Ensure AMap key is set:

   ```
   AMAP_API_KEY=your-amap-key
   ```

2. Verify key is approved for Web Services API (not just JavaScript API)

3. Check daily quota limits on AMap console

4. Use appropriate map provider in code:
   ```python
   from tools.map_rt import set_map_provider
   set_map_provider("amap")  # For Chinese locations
   ```

---

## Runtime Errors

### Event Loop Already Running

**Problem:** `asyncio.run() cannot be called from a running event loop`

**Solution:** This has been fixed in the frontend. If you encounter this:

- Ensure you're using the latest code
- Use `await run_sitesage_session_async()` in async contexts
- Use `run_sitesage_session()` in sync contexts (CLI only)

### Agent Tool Call Failures

**Problem:** Agent gets stuck or fails with tool errors

**Solutions:**

1. Check tool-specific logs in terminal for actual error

2. Verify data files are accessible:

   - WorldPop rasters in correct location
   - File permissions are correct

3. Increase timeout if network issues:

   - Check your internet connection
   - Try again during off-peak hours

4. Review session artifacts for partial results:
   ```bash
   ls src/save/<session_id>/
   ```

### JSON Parsing Errors

**Problem:** `JSONDecodeError` when processing LLM responses

**Solutions:**

1. This is usually a temporary LLM issue. Retry the analysis.

2. Check OpenAI API status: https://status.openai.com/

3. Review the last saved report to see where it failed:

   ```bash
   ls -lt src/save/<session_id>/
   ```

4. If persistent, the prompt may be too complex. Simplify it.

---

## Map and Data Issues

### Geocoding Failures

**Problem:** Location not found or incorrect coordinates

**Solutions:**

1. Be more specific in location description:

   - ✅ Good: "1600 Amphitheatre Parkway, Mountain View, CA"
   - ❌ Bad: "near downtown"

2. Include city and country for international locations:

   - ✅ "南京东路 300 号, 黄浦区, 上海市, 中国"

3. Use well-known landmarks if exact address is unavailable

4. Check the `01_understanding.md` report for geocoded location

5. Verify correct map provider for region:
   - Google Maps for US/Europe
   - AMap for China

### Map Not Rendering in UI

**Problem:** Blank map or loading errors in browser

**Solutions:**

1. Check browser console (F12) for errors

2. Verify internet connection (map uses OpenStreetMap tiles)

3. Try different tile provider (UI has automatic fallback)

4. Clear browser cache and refresh

5. Check if firewall/proxy is blocking map tile requests

### No Population Data

**Problem:** Customer analysis shows `population_total: null`

**Solutions:**

1. Verify WorldPop raster files are available:

   ```python
   from tools.demographics import DemographicsTool
   tool = DemographicsTool()
   # Check configured paths
   ```

2. Ensure location is within raster coverage area

3. Check file permissions on raster files

4. Location may be in ocean/unpopulated area (expected null)

### Distance/POI Search Returns No Results

**Problem:** "No nearby transit found" or empty competitor lists

**Solutions:**

1. Increase search radius (LLM agent should do this automatically)

2. Location may be in rural/remote area (valid result)

3. Try different POI types:

   ```python
   # In agent prompts
   types = ["subway_station", "train_station", "bus_station"]
   ```

4. Check API quota limits (Google Maps/AMap)

---

## Performance Issues

### Slow Analysis (>2 minutes)

**Problem:** Analysis takes longer than expected

**Causes & Solutions:**

1. **OpenAI API latency**:

   - Normal for complex analyses
   - Peak usage times may be slower
   - Use gpt-4o-mini for faster results (lower quality)

2. **Tool call iterations**:

   - Agents may make multiple tool calls
   - Check terminal logs to see progress
   - This is expected behavior

3. **Network issues**:

   - Slow internet connection
   - API rate limiting
   - Try again or check connection

4. **Large search radius**:
   - Smaller areas process faster
   - More POIs = more data to process

### High Memory Usage

**Problem:** Python process uses excessive memory

**Solutions:**

1. Process one analysis at a time (close browser tabs)

2. Restart server periodically:

   ```bash
   # Ctrl+C to stop
   python sitesage_frontend.py
   ```

3. Clear old session data:

   ```bash
   rm -rf src/save/old_session_*
   ```

4. Reduce concurrent requests (if using API programmatically)

---

## UI/Frontend Issues

### Artifacts Not Displaying

**Problem:** Clicking artifact links shows blank page or 404

**Solutions:**

1. Verify files exist:

   ```bash
   ls src/save/<session_id>/
   ```

2. Check file paths in API response:

   - Should be `/save/<session_id>/filename.md`
   - Not absolute file system paths

3. Refresh page and try again

4. Check browser console for JavaScript errors

### Markdown Not Rendering

**Problem:** Raw markdown text shown instead of formatted HTML

**Solutions:**

1. Check if Marked.js library loaded:

   - Open browser console (F12)
   - Type `marked` and press Enter
   - Should show function definition

2. Internet connection required for CDN resources

3. Use local copy of Marked.js if needed:
   ```html
   <script src="./marked.min.js"></script>
   ```

### UI Not Loading

**Problem:** Blank page or "Connection refused" error

**Solutions:**

1. Verify server is running:

   ```bash
   cd src
   python sitesage_frontend.py
   ```

   Look for: `INFO: Application startup complete.`

2. Check correct URL:

   - Should be `http://127.0.0.1:8000`
   - NOT `https://` (no SSL)

3. Port may be in use:

   ```bash
   # Change port in sitesage_frontend.py
   uvicorn.run(app, host="127.0.0.1", port=8001)
   ```

4. Firewall blocking port 8000:
   - Add exception for Python/port 8000
   - Or use different port

---

## Getting Help

If you continue to experience issues:

1. **Check logs**: Review terminal output for error details

2. **Session artifacts**: Examine saved reports in `src/save/<session_id>/`

3. **GitHub Issues**: Search existing issues or create new one

4. **Documentation**: Review [DESIGN.md](DESIGN.md) and [API.md](API.md)

5. **Minimal reproduction**: Try with simple example:
   ```
   Open a coffee shop near Central Park, New York City.
   ```

---

## Debug Mode

For detailed debugging:

1. **Enable verbose logging**:

   ```python
   # In sitesage_backend.py
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check railtracks state files**:

   ```bash
   ls .railtracks/
   ```

3. **Test individual tools**:

   ```python
   cd src
   python
   >>> from tools.map_rt import tool_get_place_info
   >>> result = tool_get_place_info("Times Square, NYC", "New York")
   >>> print(result)
   ```

4. **Inspect API responses**:
   - Add `print()` statements in tool wrappers
   - Save raw responses to files

---

## Known Issues

### Temporary Issues

- LLM response variability (normal behavior)
- Occasional API timeouts (retry)
- Map tile loading delays (CDN dependent)

### By Design

- Limited to coffee shops in prototype (extensible)
- Requires internet connectivity
- API keys needed for full functionality
- Analysis takes 30-120 seconds (LLM processing)

---

## Contact

For issues not covered here:

- Open a GitHub issue with:
  - Error message (full stack trace)
  - Steps to reproduce
  - Environment details (OS, Python version)
  - Session ID if applicable
