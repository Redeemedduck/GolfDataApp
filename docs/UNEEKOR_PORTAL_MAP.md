# Uneekor Portal Navigation Map

This document maps the Uneekor portal structure for automated session discovery and import.

## Portal Overview

| Property | Value |
|----------|-------|
| **Base URL** | `https://my.uneekor.com` |
| **Reports Page** | `/report` |
| **Report Detail** | `/power-u-report?id={ID}&key={KEY}` |
| **Total Reports** | 111 (as of 2026-01-26) |
| **Date Range** | Mar 2024 - Jan 2026 |

---

## Navigation Structure

### Main Navigation (Sidebar)
```
/dashboard      - User dashboard
/subscription   - Subscription management
/inventory      - Equipment inventory
/report         - Power U Reports (SESSION DATA)
/claim/*        - Promotions/claims
/support        - Support page
```

### Reports Page Layout

```
+--------------------------------------------------+
|  UNEEKOR                           [User] [Menu] |
+--------------------------------------------------+
|                                                  |
|                    Report                        |
|                                                  |
|  Power U Report (VIEW)         [30 v] [Search]   |
|                                                  |
|  +--------------------------------------------+  |
|  | session_name                          [^]  |  |  <- Collapsed row
|  +--------------------------------------------+  |
|  | session_name                          [v]  |  |  <- Expanded row
|  |   +--------------------------------------+ |  |
|  |   | session_name                        | |  |
|  |   | Date:      Jan 25, 2026             | |  |
|  |   | Username:  matt                     | |  |
|  |   | Shots:     41                       | |  |
|  |   |                    [Open ->]        | |  |
|  |   +--------------------------------------+ |  |
|  +--------------------------------------------+  |
|  | ...more sessions...                        |  |
|  +--------------------------------------------+  |
|                                                  |
|              [<] [1] [2] [3] [4] [>]             |  <- Pagination
|                                                  |
+--------------------------------------------------+
```

---

## Controls Reference

### Items Per Page Dropdown
- **Selector**: `#itemLimit` or `combobox` near "Power U Report"
- **Options**: 5, 10, 20, 30
- **Default**: 5
- **Recommendation**: Set to 30 for efficient scraping

### Pagination
- **Selector**: `navigation > list > button`
- **Pattern**: `button[name="1"]`, `button[name="2"]`, etc.
- **Next/Prev**: Arrow buttons at start/end of pagination
- **Current**: Button with `[active]` attribute

### Session Rows
- **Collapsed**: `button` with session name text
- **Expanded**: Click row to reveal details panel
- **Details Panel Contains**:
  - Session name (header)
  - Date (e.g., "Jan 25, 2026")
  - Username
  - Shot count
  - "Open" link to report detail page

### Search
- **Selector**: `textbox[placeholder="Enter search keyword here"]`
- **Behavior**: Filters visible sessions by name

---

## URL Patterns

### Reports List
```
https://my.uneekor.com/report
```

### Individual Report
```
https://my.uneekor.com/power-u-report?id={REPORT_ID}&key={API_KEY}&distance=yard&speed=mph
```

**Parameters:**
| Param | Description | Example |
|-------|-------------|---------|
| `id` | Unique report ID | `43285` |
| `key` | API authentication key | `CqueGwWNXRZU5cCB` |
| `distance` | Distance unit | `yard` or `meter` |
| `speed` | Speed unit | `mph` or `kph` |

---

## Data Extraction Strategy

### Step 1: Set Pagination to 30
```javascript
await page.locator('#itemLimit').selectOption(['30']);
```

### Step 2: Extract All Links Per Page
```javascript
const links = document.querySelectorAll('a[href*="power-u-report"]');
const sessions = Array.from(links).map(a => {
  const match = a.href.match(/id=(\d+)&key=([^&]+)/);
  return match ? { id: match[1], key: match[2], url: a.href } : null;
}).filter(Boolean);
```

### Step 3: Get Session Names (requires expansion)
```javascript
// Click each session button to expand
// Parse the expanded panel for: name, date, username, shots
```

### Step 4: Navigate Pages
```javascript
// Click page buttons: 1, 2, 3, 4
// Or click next arrow until disabled
```

---

## Inventory Summary (2026-01-26)

| Page | Reports | Date Range |
|------|---------|------------|
| 1 | 30 | Jan 2026 (recent) |
| 2 | 30 | Mar 2025 - Dec 2025 |
| 3 | 30 | Dec 2024 - Mar 2025 |
| 4 | 21 | Mar 2024 - Dec 2024 |
| **Total** | **111** | **Mar 2024 - Jan 2026** |

### Session Naming Patterns Observed
- Custom names: `warmup`, `par 3`, `driver`, `sgt rd1`, `bag mapping`
- Club-based: `Iron 6`, `Driver`, `Wedge Pitching`, `Wood 3`
- Course names: `candlestone`, `estes park`, `silvertip`, `torrey north`
- Tournament: `sgt plantation course`, `sgt shadowridge rd2`
- Practice: `3/4 speed towel drill`, `dst trainer`, `60 shot challenge`
- Default format: `DRIVER | MEDIUM`, `IRON7 | PREMIUM`

---

## Authentication

### Cookie-Based Session
- Login creates session cookies
- Cookies stored encrypted in `automation/cookies.enc`
- Default expiry: ~7 days
- CLI command: `python automation_runner.py login`

### Required for Access
- Valid session cookies OR
- Fresh login via `/login` page

---

## Screenshots Reference

| File | Description |
|------|-------------|
| `portal-inventory-page1-expanded.png` | Page 1 with expanded session |
| `uneekor-30-sessions.png` | Full page 1 at 30 items |
| `uneekor-session-expanded.png` | Session detail panel |

---

## Implementation Notes

1. **Always set items to 30** before scraping to minimize page navigation
2. **Session names** are only visible in collapsed rows or expanded panels
3. **Dates** require expanding each row (not visible in collapsed state)
4. **Deduplication**: Links appear twice per session (hidden + "Open" button)
5. **Rate limiting**: Portal may throttle rapid requests - use delays

---

## Related Files

| File | Purpose |
|------|---------|
| `automation/uneekor_portal.py` | Portal navigation class |
| `automation/session_discovery.py` | Session discovery logic |
| `automation/inventory/reports_inventory.json` | Full inventory data |
| `docs/UNEEKOR_REPORT_PAGE_MAP.md` | Individual report page structure |
