# Implementation Plan: Golf Data App Refactoring

**Created**: December 26, 2024
**Goal**: Improve efficiency, reduce redundancy, create clean component separation
**Estimated Duration**: 2-3 weeks

---

## 📋 Overview

This plan refactors the golf data application into three clean components:

1. **Service Layer** - Business logic and orchestration
2. **Vertex AI Agent** - Unified AI coaching service
3. **Optimized Scraper** - Efficient data collection with caching

---

## 🏗️ PHASE 1: SERVICE LAYER STRUCTURE

**Duration**: 3-4 days
**Goal**: Create clean separation between UI, business logic, and data access

### Architecture

```
services/
├── __init__.py
├── base_service.py          # Base class with logging
├── data_service.py          # Unified database operations
├── media_service.py         # Media caching and optimization
├── import_service.py        # Import orchestration
└── ai_coach_service.py      # Unified AI interface (Phase 2)

repositories/
├── __init__.py
├── base_repository.py       # Base repository pattern
├── shot_repository.py       # Shot data access
└── media_repository.py      # Media storage access
```

### Task 1.1: Design Service Architecture (30 min)

**Create folder structure:**
```bash
mkdir -p services repositories
touch services/__init__.py repositories/__init__.py
```

**Design decisions:**
- Services handle business logic, repositories handle data access
- All services inherit from BaseService for consistent logging
- Repository pattern abstracts database implementation
- Dependency injection for testability

### Task 1.2: Create Base Service Class (1 hour)

**File**: `services/base_service.py`

**Features:**
- Structured logging with context
- Error handling patterns
- Performance metrics
- Configuration management

**Key methods:**
```python
class BaseService:
    def __init__(self, config: dict = None)
    def _log_info(self, message: str, **context)
    def _log_error(self, message: str, error: Exception, **context)
    def _handle_error(self, error: Exception, context: str)
    def _track_performance(self, operation: str)
```

### Task 1.3: Implement DataService (3 hours)

**File**: `services/data_service.py`

**Purpose**: Unified interface for all database operations

**Current Issues to Fix:**
- `golf_db.py:102-160` - Duplicate save logic for SQLite and Supabase
- No abstraction between storage backends
- Hard to test due to tight coupling

**New Implementation:**
```python
class DataService(BaseService):
    """Unified data operations across all storage backends"""

    def __init__(self):
        self.shot_repo = ShotRepository()
        self.session_repo = SessionRepository()

    async def save_shot(self, shot_data: dict) -> str:
        """Save shot to all configured backends"""

    async def get_shots(self, filters: dict = None) -> List[dict]:
        """Retrieve shots with filtering"""

    async def get_session(self, session_id: str) -> dict:
        """Get complete session with all shots"""

    async def delete_shot(self, shot_id: str) -> bool:
        """Delete shot from all backends"""

    async def update_club_name(self, old_name: str, new_name: str) -> int:
        """Rename club across all shots"""
```

**Migration Path:**
1. Create new DataService alongside existing golf_db.py
2. Gradually migrate calls from app.py
3. Deprecate golf_db.py once migration complete

### Task 1.4: Implement MediaService (4 hours)

**File**: `services/media_service.py`

**Purpose**: Intelligent media handling with caching

**Current Issues to Fix:**
- `golf_scraper.py:156-258` - Downloads all media every time
- No caching mechanism
- No deduplication

**New Implementation:**
```python
class MediaService(BaseService):
    """Intelligent media handling with caching"""

    def __init__(self):
        self.media_repo = MediaRepository()
        self.cache = MediaCache()

    async def process_shot_media(
        self,
        shot_id: str,
        api_params: dict,
        strategy: str = "keyframes"
    ) -> dict:
        """Process media with caching and optimization"""

    async def download_frames(
        self,
        shot_id: str,
        frame_urls: List[str],
        skip_existing: bool = True
    ) -> List[str]:
        """Download video frames with smart caching"""

    async def optimize_image(self, image_path: str) -> str:
        """Optimize image size/quality"""

    def check_media_exists(self, shot_id: str) -> dict:
        """Check if media already exists locally/cloud"""
```

**Caching Strategy:**
```
1. Check if media exists in local cache → return cached URLs
2. Check if media exists in cloud storage → download to cache
3. Download from Uneekor API → cache → upload to cloud
4. Return final URLs
```

### Task 1.5: Implement ImportService (3 hours)

**File**: `services/import_service.py`

**Purpose**: Orchestrate the complete import workflow

**Current Issues to Fix:**
- Import logic scattered between app.py and golf_scraper.py
- No progress tracking abstraction
- Hard to test end-to-end flow

**New Implementation:**
```python
class ImportService(BaseService):
    """Orchestrate shot import workflow"""

    def __init__(self):
        self.data_service = DataService()
        self.media_service = MediaService()
        self.scraper = UneekorScraper()

    async def import_report(
        self,
        url: str,
        progress_callback: Callable[[str, int, int], None] = None
    ) -> dict:
        """Complete import workflow"""
        # 1. Scrape data from API
        # 2. Process media
        # 3. Save to database
        # 4. Return summary

    async def import_shot(self, shot_data: dict) -> str:
        """Import single shot"""

    def validate_url(self, url: str) -> bool:
        """Validate Uneekor URL format"""
```

**Usage in app.py:**
```python
# Before:
shots = golf_scraper.run_scraper(url, progress_bar)
for shot in shots:
    golf_db.save_shot(shot)

# After:
import_service = ImportService()
result = await import_service.import_report(
    url,
    progress_callback=lambda msg, current, total: progress_bar.progress(current/total)
)
st.success(f"Imported {result['shot_count']} shots")
```

### Task 1.6: Create Repository Layer (4 hours)

**File**: `repositories/base_repository.py`
```python
class BaseRepository:
    """Base repository with common data access patterns"""

    def __init__(self, connection):
        self.connection = connection

    async def find_by_id(self, id: str)
    async def find_all(self, filters: dict = None)
    async def save(self, entity: dict)
    async def update(self, id: str, updates: dict)
    async def delete(self, id: str)
```

**File**: `repositories/shot_repository.py`
```python
class ShotRepository(BaseRepository):
    """Shot data access with multi-backend support"""

    def __init__(self):
        self.sqlite = SQLiteConnection()
        self.supabase = SupabaseConnection()

    async def save(self, shot: dict) -> str:
        """Save to both SQLite and Supabase"""

    async def find_by_session(self, session_id: str) -> List[dict]:
        """Get all shots in a session"""

    async def find_with_filters(self, club: str = None, date_range: tuple = None):
        """Complex filtering"""
```

**File**: `repositories/media_repository.py`
```python
class MediaRepository(BaseRepository):
    """Media storage access (Supabase Storage)"""

    async def upload(self, file_path: str, bucket: str) -> str:
        """Upload file and return public URL"""

    async def download(self, url: str, local_path: str):
        """Download media to local cache"""

    async def exists(self, shot_id: str, media_type: str) -> bool:
        """Check if media exists in storage"""

    async def delete(self, url: str):
        """Delete media from storage"""
```

### Task 1.7: Update app.py (2 hours)

**Changes Required:**

1. **Import Data Tab** (app.py:~180-240)
```python
# Before:
if st.button("Run Scraper"):
    shots = golf_scraper.run_scraper(url, progress_bar)

# After:
if st.button("Import Report"):
    import_service = ImportService()
    result = await import_service.import_report(url, progress_callback)
```

2. **Shot Viewer Tab** (app.py:~240-350)
```python
# Before:
all_shots = golf_db.get_all_shots()

# After:
data_service = DataService()
all_shots = await data_service.get_shots()
```

3. **Manage Data Tab** (app.py:~350-450)
```python
# Before:
golf_db.update_club_name(old, new)

# After:
data_service = DataService()
await data_service.update_club_name(old, new)
```

### Task 1.8: Testing (2 hours)

**Test Plan:**

1. **Unit Tests**
```python
# tests/test_data_service.py
def test_save_shot():
    service = DataService()
    shot_id = await service.save_shot(sample_shot_data)
    assert shot_id is not None

# tests/test_media_service.py
def test_media_caching():
    service = MediaService()
    urls = await service.process_shot_media(shot_id, api_params)
    # Second call should use cache
    urls2 = await service.process_shot_media(shot_id, api_params)
    assert urls == urls2
```

2. **Integration Tests**
```python
# tests/test_import_service.py
def test_complete_import_flow():
    service = ImportService()
    result = await service.import_report(test_url)
    assert result['shot_count'] > 0
    assert result['errors'] == 0
```

3. **Manual Testing**
- Import a new report through Streamlit
- Verify shots appear in Shot Viewer
- Check media displays correctly
- Test rename club functionality
- Verify data in both SQLite and Supabase

---

## 🤖 PHASE 2: VERTEX AI AGENT

**Duration**: 2-3 days
**Goal**: Implement professional AI coaching with conversation memory

### Architecture

```
services/
├── ai_coach_service.py      # Unified AI interface
└── vertex_agent_service.py  # Vertex AI implementation

vertex_tools/
├── __init__.py
├── bigquery_tool.py         # Direct BigQuery access
├── analysis_tool.py         # Swing analysis
├── visualization_tool.py    # Chart generation
└── recommendation_tool.py   # Practice suggestions
```

### Task 2.1: Set Up Vertex AI Agent Builder (1 hour)

**GCP Console Steps:**
1. Navigate to Vertex AI > Agent Builder
2. Create new agent: "golf-coach-agent"
3. Configure model: `gemini-2.0-flash-exp`
4. Enable code execution
5. Set up data stores (BigQuery connection)

**Required Permissions:**
```bash
gcloud projects add-iam-policy-binding valued-odyssey-474423-g1 \
  --member="user:YOUR_EMAIL" \
  --role="roles/aiplatform.user"
```

### Task 2.2: Create VertexAgentService (3 hours)

**File**: `services/vertex_agent_service.py`

```python
class VertexAgentService(BaseService):
    """Vertex AI Agent with custom tools"""

    def __init__(self):
        self.agent = self._initialize_agent()
        self.session_manager = SessionManager()

    def _initialize_agent(self):
        """Configure agent with tools"""
        return VertexAIAgent(
            project="valued-odyssey-474423-g1",
            location="us-central1",
            agent_id="golf-coach-agent",
            tools=[
                BigQueryTool(),
                AnalyzeSwingTool(),
                CompareSessionsTool(),
                GenerateChartTool(),
                SuggestDrillsTool()
            ]
        )

    async def chat(
        self,
        message: str,
        session_id: str,
        user_data: dict = None
    ) -> dict:
        """Multi-turn conversation"""
        context = self.session_manager.get_context(session_id)

        response = await self.agent.generate(
            message=message,
            context=context,
            user_data=user_data
        )

        self.session_manager.update(session_id, message, response)

        return {
            'text': response.text,
            'charts': response.charts,
            'recommendations': response.recommendations
        }
```

### Task 2.3: Define Custom Tools (4 hours)

**File**: `vertex_tools/bigquery_tool.py`
```python
class BigQueryTool(VertexTool):
    """Direct BigQuery access for historical data"""

    def get_schema(self):
        return {
            "name": "query_bigquery",
            "description": "Query golf shot history from BigQuery",
            "parameters": {
                "query": "SQL query string",
                "club": "Optional club filter",
                "date_range": "Optional date range"
            }
        }

    async def execute(self, params: dict) -> dict:
        client = bigquery.Client()
        query = self._build_safe_query(params)
        df = client.query(query).to_dataframe()
        return df.to_dict(orient='records')
```

**File**: `vertex_tools/analysis_tool.py`
```python
class AnalyzeSwingTool(VertexTool):
    """Analyze swing metrics and identify issues"""

    async def execute(self, params: dict) -> dict:
        shot_data = params['shot_data']

        issues = []
        if abs(shot_data['club_path']) > 3:
            issues.append({
                'type': 'club_path',
                'severity': 'high',
                'recommendation': 'Work on swing path drills'
            })

        return {
            'issues': issues,
            'strengths': self._identify_strengths(shot_data),
            'improvement_areas': self._prioritize_improvements(shot_data)
        }
```

**File**: `vertex_tools/visualization_tool.py`
```python
class GenerateChartTool(VertexTool):
    """Generate Plotly charts"""

    async def execute(self, params: dict) -> dict:
        chart_type = params['type']
        data = params['data']

        if chart_type == 'dispersion':
            return self._create_dispersion_chart(data)
        elif chart_type == 'trend':
            return self._create_trend_chart(data)

        return {'chart': fig.to_json()}
```

### Task 2.4: Implement Session Management (2 hours)

**File**: `services/session_manager.py`
```python
class SessionManager:
    """Manage conversation context and memory"""

    def __init__(self):
        self.sessions = {}  # In-memory for now, migrate to Firestore later

    def get_context(self, session_id: str) -> dict:
        """Retrieve conversation history"""

    def update(self, session_id: str, message: str, response: dict):
        """Add to conversation history"""

    def summarize_context(self, session_id: str) -> str:
        """Summarize long conversations to save tokens"""
```

### Task 2.5: Create AICoachService (2 hours)

**File**: `services/ai_coach_service.py`

**Purpose**: Provider-agnostic AI interface

```python
class AICoachService(BaseService):
    """Unified AI interface supporting multiple providers"""

    def __init__(self, provider: str = "vertex"):
        self.providers = {
            "vertex": VertexAgentService(),
            "gemini": GeminiService(),
            "anthropic": AnthropicService()
        }
        self.active_provider = self.providers[provider]

    async def analyze_session(
        self,
        session_data: dict,
        question: str = None
    ) -> dict:
        """Provider-agnostic analysis"""
        return await self.active_provider.chat(
            message=question or "Analyze this session",
            user_data=session_data
        )

    async def get_coaching_insights(
        self,
        shot_data: dict
    ) -> dict:
        """Get specific coaching recommendations"""
```

### Task 2.6: Integrate with Streamlit (2 hours)

**Update AI Coach Tab** (app.py:~450-600)

```python
# Initialize service
if 'ai_coach_service' not in st.session_state:
    st.session_state.ai_coach_service = AICoachService(provider="vertex")
    st.session_state.chat_session_id = str(uuid.uuid4())

# Chat interface with history
for message in st.session_state.chat_history:
    with st.chat_message(message['role']):
        st.write(message['content'])
        if 'chart' in message:
            st.plotly_chart(message['chart'])

# User input
if prompt := st.chat_input("Ask about your golf game..."):
    # Add user message
    st.session_state.chat_history.append({'role': 'user', 'content': prompt})

    # Get AI response
    response = await st.session_state.ai_coach_service.analyze_session(
        session_data=current_session_data,
        question=prompt
    )

    # Add AI response
    st.session_state.chat_history.append({
        'role': 'assistant',
        'content': response['text'],
        'chart': response.get('chart'),
        'recommendations': response.get('recommendations')
    })
```

### Task 2.7: Testing (2 hours)

**Test Scenarios:**

1. **Multi-turn Conversation**
```
User: "Show me my Driver stats"
Agent: [Shows stats]
User: "Now compare to last week"
Agent: [Remembers context, compares]
```

2. **Tool Calling**
```
User: "Create a dispersion chart for my 7-iron"
Agent: [Uses GenerateChartTool, returns Plotly chart]
```

3. **BigQuery Integration**
```
User: "How has my club path improved over time?"
Agent: [Queries BigQuery, analyzes trend]
```

---

## 🎯 PHASE 3: OPTIMIZED SCRAPER

**Duration**: 2-3 days
**Goal**: Fast, efficient data collection with caching

### Task 3.1: Add Media Caching (3 hours)

**File**: `services/media_cache.py`

```python
class MediaCache:
    """Local media caching system"""

    def __init__(self, cache_dir: str = "./media_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.index = self._load_index()

    def get(self, shot_id: str, media_type: str) -> Optional[str]:
        """Get cached media path"""

    def put(self, shot_id: str, media_type: str, file_path: str):
        """Add to cache"""

    def exists(self, shot_id: str, media_type: str) -> bool:
        """Check if media is cached"""

    def get_checksum(self, file_path: str) -> str:
        """Calculate file checksum for deduplication"""
```

**Integration with MediaService:**
```python
async def process_shot_media(self, shot_id, api_params):
    # Check cache first
    if self.cache.exists(shot_id, 'impact_img'):
        return self.cache.get(shot_id, 'impact_img')

    # Download if not cached
    image_data = await self._download_from_api(api_params)

    # Cache locally
    cache_path = self.cache.put(shot_id, 'impact_img', image_data)

    # Upload to cloud
    cloud_url = await self.media_repo.upload(cache_path)

    return cloud_url
```

### Task 3.2: Implement Deduplication (2 hours)

**File**: `services/media_service.py`

```python
def calculate_checksum(self, file_path: str) -> str:
    """Calculate SHA256 checksum"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

async def upload_with_dedup(self, file_path: str) -> str:
    """Upload only if content is unique"""
    checksum = self.calculate_checksum(file_path)

    # Check if this exact file already exists
    existing_url = await self.media_repo.find_by_checksum(checksum)
    if existing_url:
        self._log_info(f"Skipping duplicate upload: {checksum}")
        return existing_url

    # Upload new file
    return await self.media_repo.upload(file_path, checksum=checksum)
```

### Task 3.3: Decouple Scraper from Database (3 hours)

**File**: `scrapers/uneekor_scraper.py` (new, refactored)

```python
class UneekorScraper:
    """Pure scraping logic without dependencies"""

    def __init__(self):
        self.base_url = "https://api-v2.golfsvc.com/v2/oldmyuneekor/report"

    async def scrape_report(self, url: str) -> List[dict]:
        """Returns structured data without saving"""
        report_id, key = self._extract_params(url)

        # Fetch from API
        api_data = await self._fetch_api_data(report_id, key)

        # Process and structure data
        shots = []
        for session in api_data:
            for shot in session['shots']:
                processed = self._process_shot(shot, report_id, session['id'])
                shots.append(processed)

        return shots  # Return data, don't save

    def _process_shot(self, shot: dict, report_id: str, session_id: str) -> dict:
        """Process single shot data"""
        return {
            'shot_id': f"{report_id}_{session_id}_{shot['id']}",
            'session_id': f"{report_id}_{session_id}",
            'session_date': self._extract_date(shot),
            'club': shot.get('club'),
            'carry': self._convert_distance(shot.get('carry')),
            'ball_speed': self._convert_speed(shot.get('ball_speed')),
            # ... all other fields
            'api_media_params': {
                'report_id': report_id,
                'key': self._key,
                'session_id': session_id,
                'shot_id': shot['id']
            }
        }
```

**Update ImportService:**
```python
async def import_report(self, url: str, progress_callback) -> dict:
    # 1. Scrape data (no database calls)
    scraper = UneekorScraper()
    shots = await scraper.scrape_report(url)

    total = len(shots)
    imported = 0
    errors = []

    for i, shot in enumerate(shots):
        try:
            # 2. Process media (with caching)
            media_urls = await self.media_service.process_shot_media(
                shot['shot_id'],
                shot['api_media_params']
            )
            shot.update(media_urls)

            # 3. Save to database
            shot_id = await self.data_service.save_shot(shot)
            imported += 1

            # 4. Update progress
            if progress_callback:
                progress_callback(f"Imported shot {i+1}/{total}", i+1, total)

        except Exception as e:
            errors.append({'shot': shot['shot_id'], 'error': str(e)})
            self._log_error(f"Failed to import shot", e)

    return {
        'shot_count': imported,
        'error_count': len(errors),
        'errors': errors
    }
```

### Task 3.4: Add Retry Logic (2 hours)

**File**: `scrapers/uneekor_scraper.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class UneekorScraper:

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _fetch_api_data(self, report_id: str, key: str) -> dict:
        """Fetch from API with automatic retry"""
        url = f"{self.base_url}/{report_id}/{key}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=30) as response:
                if response.status == 429:
                    # Rate limited, wait and retry
                    await asyncio.sleep(5)
                    raise Exception("Rate limited")

                response.raise_for_status()
                return await response.json()

    @retry(stop=stop_after_attempt(2))
    async def _download_image(self, url: str) -> bytes:
        """Download image with retry"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
```

### Task 3.5: Optimize Frame Downloads (3 hours)

**File**: `services/media_service.py`

**Current**: Downloads frames sequentially
**Optimized**: Download frames in parallel

```python
async def download_frames_parallel(
    self,
    shot_id: str,
    frame_urls: List[str],
    max_concurrent: int = 5
) -> List[str]:
    """Download multiple frames concurrently"""

    # Check which frames already exist
    existing = await self._check_existing_frames(shot_id)
    needed = [url for url in frame_urls if url not in existing]

    if not needed:
        self._log_info(f"All frames cached for {shot_id}")
        return existing

    # Download needed frames in parallel
    semaphore = asyncio.Semaphore(max_concurrent)

    async def download_with_limit(url, index):
        async with semaphore:
            return await self._download_frame(shot_id, url, index)

    tasks = [
        download_with_limit(url, i)
        for i, url in enumerate(needed)
    ]

    downloaded = await asyncio.gather(*tasks, return_exceptions=True)

    # Combine existing + newly downloaded
    all_frames = existing + [f for f in downloaded if not isinstance(f, Exception)]

    return all_frames
```

### Task 3.6: Update ImportService (1 hour)

**File**: `services/import_service.py`

```python
async def import_report(self, url: str, progress_callback) -> dict:
    # Use optimized scraper
    scraper = UneekorScraper()
    shots = await scraper.scrape_report(url)

    # Batch process media (parallel downloads)
    media_tasks = [
        self.media_service.process_shot_media(
            shot['shot_id'],
            shot['api_media_params']
        )
        for shot in shots
    ]

    # Process all media in parallel
    media_results = await asyncio.gather(*media_tasks, return_exceptions=True)

    # Save to database
    for shot, media in zip(shots, media_results):
        if isinstance(media, Exception):
            self._log_error(f"Media processing failed for {shot['shot_id']}", media)
            continue

        shot.update(media)
        await self.data_service.save_shot(shot)
```

### Task 3.7: Performance Testing (2 hours)

**Test Script**: `tests/test_import_performance.py`

```python
import time

async def test_import_speed():
    """Compare old vs new import speed"""

    test_url = "YOUR_TEST_URL"

    # Old method (baseline)
    start = time.time()
    old_result = golf_scraper.run_scraper(test_url)
    old_duration = time.time() - start

    # New method
    start = time.time()
    import_service = ImportService()
    new_result = await import_service.import_report(test_url)
    new_duration = time.time() - start

    print(f"Old method: {old_duration:.2f}s")
    print(f"New method: {new_duration:.2f}s")
    print(f"Improvement: {(1 - new_duration/old_duration)*100:.1f}%")

    # Second import (should be faster due to caching)
    start = time.time()
    cached_result = await import_service.import_report(test_url)
    cached_duration = time.time() - start

    print(f"Cached import: {cached_duration:.2f}s")
    print(f"Cache speedup: {(1 - cached_duration/new_duration)*100:.1f}%")
```

**Expected Results:**
- First import: 2-3x faster (parallel downloads)
- Cached import: 10x faster (no downloads needed)

---

## 📊 Success Metrics

### Phase 1 Success Criteria
- ✅ All UI functions work through service layer
- ✅ Database operations abstracted behind repositories
- ✅ No direct database calls from app.py
- ✅ Unit tests pass for all services
- ✅ Integration tests pass end-to-end

### Phase 2 Success Criteria
- ✅ Multi-turn conversations work with context memory
- ✅ Custom tools execute successfully
- ✅ BigQuery integration returns correct data
- ✅ Visualizations display in Streamlit
- ✅ Response time < 3 seconds

### Phase 3 Success Criteria
- ✅ Import speed improved by 2-3x
- ✅ Cached imports 10x faster
- ✅ Media deduplication working
- ✅ Cache hit rate > 80% on re-imports
- ✅ Zero duplicate uploads

---

## 🚀 Getting Started with Phase 1

**Next Steps:**
1. Review this plan
2. Start with Task 1.1 (Create folder structure)
3. Build incrementally, test frequently
4. Commit after each major task
5. Update CLAUDE.md as architecture evolves

**Ready to begin?** Let's start with creating the service architecture!
