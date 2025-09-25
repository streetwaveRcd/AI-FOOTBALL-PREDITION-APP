// Global state
afterLoad = false;
let autoRefreshInterval = null;
let nextRefreshSeconds = 600; // 10 minutes

// Current tab state
let currentTab = 'live';

// Authentication state
let currentUser = null;
let isAuthenticated = false;
let ipUsage = {
  request_count: 0,
  limit_exceeded: false,
  remaining_requests: 5
};

// Prediction batch management
let currentPredictions = [];
let availableBatches = [];
let selectedBatchId = null;

// Global IP location data for time conversion
let userLocationData = {
  timezone: null,
  country_code: null,
  city: null,
  country: null,
  loaded: false
};

// Settings management
let userSettings = {
  refreshInterval: 600, // 10 minutes default
  autoRefreshEnabled: true,
  animationsEnabled: true,
  compactMode: false
};

// Fetch cache to limit requests (all tabs share)
let cachedData = {
  competitions: null,
  live: null,
  upcoming: null,
  predictions: null,
  results: null,
  comparison: null,
  timestamp: 0
};

// DOM elements
const liveTabBtnId = 'live';
const upcomingTabBtnId = 'upcoming';
const predictionsTabBtnId = 'predictions';
const resultsTabBtnId = 'results';
const comparisonTabBtnId = 'comparison';

function $(id) { return document.getElementById(id); }

function setLoading(show) {
  const overlay = $('loading-overlay');
  overlay.style.display = show ? 'block' : 'none';
}

function showError(message) {
  $('error-message').textContent = message || 'An unexpected error occurred.';
  $('error-modal').style.display = 'block';
}

function closeErrorModal() {
  $('error-modal').style.display = 'none';
}

// Tab switching
function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelector(`.tab-btn[data-tab="${tab}"]`).classList.add('active');

  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  $(`${tab}-tab`).classList.add('active');

  // Show appropriate filter strip
  const showLeagueFilter = tab === 'upcoming' || tab === 'results';
  const showPredictionFilter = tab === 'predictions';
  
  $('filter-strip').style.display = showLeagueFilter ? 'flex' : 'none';
  $('prediction-filter-strip').style.display = showPredictionFilter ? 'flex' : 'none';
  
  // Add/remove class for main content adjustment
  const mainContent = document.querySelector('.main-content');
  if (mainContent) {
    if (showLeagueFilter || showPredictionFilter) {
      mainContent.classList.add('with-filters');
    } else {
      mainContent.classList.remove('with-filters');
    }
  }

  // Load data for the selected tab
  loadAllData(false);
}

// Refresh handling
function startAutoRefresh() {
  if (autoRefreshInterval) clearInterval(autoRefreshInterval);
  
  if (!userSettings.autoRefreshEnabled) {
    $('next-refresh').textContent = 'Auto refresh disabled';
    return;
  }
  
  nextRefreshSeconds = userSettings.refreshInterval;
  updateNextRefreshLabel();
  autoRefreshInterval = setInterval(() => {
    nextRefreshSeconds -= 1;
    updateNextRefreshLabel();
    if (nextRefreshSeconds <= 0) {
      loadAllData(true);
      nextRefreshSeconds = userSettings.refreshInterval;
    }
  }, 1000);
}

function updateNextRefreshLabel() {
  const minutes = Math.floor(nextRefreshSeconds / 60);
  const seconds = String(nextRefreshSeconds % 60).padStart(2, '0');
  $('next-refresh').textContent = `Next refresh in: ${minutes}:${seconds}`;
}

function updateLastUpdated() {
  const now = new Date();
  $('last-updated').textContent = `Last updated: ${now.toLocaleString()}`;
}

$('refresh-btn')?.addEventListener('click', () => {
  const btn = $('refresh-btn');
  btn.classList.add('refreshing');
  loadAllData(true).finally(() => {
    btn.classList.remove('refreshing');
  });
});

// Fetch helpers
async function fetchJson(url, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const fullUrl = qs ? `${url}?${qs}` : url;
  const res = await fetch(fullUrl);
  if (!res.ok) {
    throw new Error(`Request failed (${res.status})`);
  }
  return res.json();
}

async function loadCompetitions() {
  if (cachedData.competitions) return cachedData.competitions;
  const data = await fetchJson('/api/competitions');
  if (data.success) {
    cachedData.competitions = data.data;
    // Populate competition dropdown
    const select = $('competition-filter');
    if (select) {
      // Clear existing options except first
      while (select.options.length > 1) select.remove(1);
      data.data.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
      });
    }
    
    // Populate country dropdown with unique countries from competitions
    const countrySelect = $('country-filter');
    if (countrySelect) {
      // Clear existing options except first
      while (countrySelect.options.length > 1) countrySelect.remove(1);
      
      // Extract unique countries
      const countries = new Map();
      data.data.forEach(c => {
        if (c.area && c.area.name) {
          countries.set(c.area.name, {
            name: c.area.name,
            code: c.area.code,
            flag: c.area.flag
          });
        }
      });
      
      // Sort countries alphabetically and add to dropdown
      Array.from(countries.values())
        .sort((a, b) => a.name.localeCompare(b.name))
        .forEach(country => {
          const opt = document.createElement('option');
          opt.value = country.name;
          opt.textContent = country.name;
          countrySelect.appendChild(opt);
        });
    }
  }
  return cachedData.competitions || [];
}

function getFilterParams() {
  const competition = $('competition-filter')?.value || '';
  const params = {};
  if (competition) params.competition = competition;
  return params;
}

function filterPredictions(predictions, outcomeFilter, dateFilter) {
  let filtered = predictions;

  // Outcome filter
  if (outcomeFilter) {
    filtered = filtered.filter(match => {
      const prediction = match.prediction;
      if (!prediction) return false;
      const predictedTeam = prediction.predicted_team;
      const confidence = prediction.confidence || 0;
      switch (outcomeFilter) {
        case 'WIN':
          return predictedTeam !== 'Draw';
        case 'DRAW':
          return predictedTeam === 'Draw';
        case 'ELITE_CONFIDENCE':
          return confidence >= 80;
        case 'HIGH_CONFIDENCE':
          return confidence >= 70 && confidence < 80;
        case 'MEDIUM_CONFIDENCE':
          return confidence >= 50 && confidence < 70;
        case 'LOW_CONFIDENCE':
          return confidence < 50;
        default:
          return true;
      }
    });
  }

  // Date filter (expects YYYY-MM-DD in user's local timezone)
  if (dateFilter) {
    filtered = filtered.filter(match => {
      if (!match.utcDate) return false;
      const d = new Date(match.utcDate);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const localDateStr = `${y}-${m}-${day}`;
      return localDateStr === dateFilter;
    });
  }

  return filtered;
}

// Handle filter changes with auto-apply
document.addEventListener('change', (e) => {
  if (['competition-filter', 'outcome-filter', 'prediction-date'].includes(e.target.id)) {
    // Auto-apply when any filter changes
    loadAllData(true);
  }
});

// Render helpers
function renderMatches(list, containerId, options = {}) {
  const container = $(containerId);
  if (!list || list.length === 0) {
    container.innerHTML = `<div class="no-matches"><i class="fas fa-info-circle"></i>No matches found.</div>`;
    return;
  }
  container.innerHTML = list.map(m => matchCardHtml(m, options)).join('');
}

function teamCrest(src) {
  if (!src) return '<div class="team-crest" style="display:inline-block"></div>';
  return `<img class="team-crest" src="${src}" alt="crest" onerror="this.style.display='none'"/>`;
}

function matchCardHtml(m, options = {}) {
  const statusClass = m.status === 'IN_PLAY' ? 'live' : (m.status === 'FINISHED' ? 'finished' : '');
  const isLive = m.status === 'IN_PLAY';
  const isFinished = m.status === 'FINISHED';
  
  // Enhanced score display
  let scoreHtml = '';
  if (m.score?.fullTime && (m.score.fullTime.home !== null && m.score.fullTime.away !== null)) {
    const homeScore = m.score.fullTime.home;
    const awayScore = m.score.fullTime.away;
    scoreHtml = `
      <div class="score-display">
        <div class="score ${isLive ? 'live' : ''}">${homeScore} - ${awayScore}</div>
      </div>
      ${m.minute ? `<div class="match-minute">${m.minute}'</div>` : ''}`;
  } else if (isLive && m.minute) {
    scoreHtml = `
      <div class="score-display">
        <div class="score live">0 - 0</div>
      </div>
      <div class="match-minute">${m.minute}'</div>`;
  } else {
    scoreHtml = `
      <div class="score-display">
        <div class="vs-text">VS</div>
      </div>`;
  }

  // Live events for in-play matches
  const liveEventsHtml = (isLive && m.live_events && m.live_events.length > 0) ? `
    <div class="live-events">
      <h5><i class="fas fa-clock"></i> Live Events</h5>
      <div class="events-list">
        ${m.live_events.map(event => `
          <div class="event-item ${event.type}">
            <span class="event-minute">${event.minute}'</span>
            <span class="event-icon">${getEventIcon(event.type)}</span>
            <span class="event-description">${event.description}</span>
          </div>
        `).join('')}
      </div>
    </div>` : '';

  // Enhanced match statistics
  const matchStatsHtml = `
    <div class="match-stats">
      ${m.match_info?.elapsed_time ? `
        <div class="stat-item">
          <span class="stat-label"><i class="fas fa-stopwatch"></i> Time:</span>
          <span class="stat-value">${m.match_info.elapsed_time}</span>
        </div>` : ''}
      ${m.match_info?.half_time_score ? `
        <div class="stat-item">
          <span class="stat-label"><i class="fas fa-clock"></i> Half Time:</span>
          <span class="stat-value">${m.match_info.half_time_score}</span>
        </div>` : ''}
      ${m.referees && m.referees.length > 0 ? `
        <div class="stat-item">
          <span class="stat-label"><i class="fas fa-user-tie"></i> Referee:</span>
          <span class="stat-value">${m.referees[0]}</span>
        </div>` : ''}
      ${m.attendance ? `
        <div class="stat-item">
          <span class="stat-label"><i class="fas fa-users"></i> Attendance:</span>
          <span class="stat-value">${m.attendance.toLocaleString()}</span>
        </div>` : ''}
      ${m.match_info?.weather ? `
        <div class="stat-item">
          <span class="stat-label"><i class="fas fa-cloud-sun"></i> Weather:</span>
          <span class="stat-value">${m.match_info.weather}</span>
        </div>` : ''}
    </div>`;
  
  // Match events for finished matches (goals, cards)
  const matchEventsHtml = isFinished ? `
    <div class="match-events-section">
      <div class="events-header">
        <h5><i class="fas fa-list-alt"></i> Match Events</h5>
        <button class="load-events-btn" data-match-id="${m.id}" data-action="load">
          <i class="fas fa-download"></i> Load Events
        </button>
      </div>
      <div class="events-container" id="events-${m.id}" style="display: none;">
        <div class="loading-events">
          <i class="fas fa-spinner fa-spin"></i> Loading match events...
        </div>
      </div>
    </div>` : '';

  // Enhanced team stats display for predictions (compact version)
  const teamStatsHtml = (m.prediction && m.prediction.team_stats) ? `
    <div class="team-stats-compact">
      <div class="stats-row">
        <div class="stat-compact">
          <span class="stat-text">Strength: ${m.prediction.team_stats.home.strength} vs ${m.prediction.team_stats.away.strength}</span>
        </div>
        <div class="stat-compact">
          <span class="stat-text">Goals: ${m.prediction.team_stats.home.goals_per_game} vs ${m.prediction.team_stats.away.goals_per_game}</span>
        </div>
      </div>
    </div>` : '';

  const predictionHtml = m.prediction ? `
    <div class="prediction-section-new">
      <!-- Main prediction banner -->
      <div class="prediction-banner">
        <div class="prediction-main">
          <div class="prediction-winner">
            <div class="winner-icon">
              ${m.prediction.predicted_team === 'Draw' ? 
                '<i class="fas fa-handshake"></i>' : 
                m.prediction.predicted_team === m.homeTeam.name ? 
                '<i class="fas fa-home"></i>' : 
                '<i class="fas fa-plane"></i>'}
            </div>
            <div class="winner-info">
              <div class="winner-title">Predicted Winner</div>
              <div class="winner-name">${m.prediction.predicted_team}</div>
            </div>
          </div>
          <div class="confidence-display">
            <div class="confidence-circle ${m.prediction.confidence >= 80 ? 'elite' : m.prediction.confidence >= 70 ? 'high' : m.prediction.confidence >= 50 ? 'medium' : 'low'}">
              <span class="confidence-number">${m.prediction.confidence}</span>
              <span class="confidence-percent">%</span>
            </div>
            <div class="confidence-label">Confidence</div>
          </div>
        </div>
        ${getPredictionSourcesHtml(m.prediction)}
      </div>
      
      <!-- Probabilities grid -->
      <div class="probabilities-grid">
        <div class="prob-card home">
          <div class="prob-header">
            <i class="fas fa-home"></i>
            <span>HomeWin</span>
          </div>
          <div class="prob-value">${m.prediction.probabilities.home_win}%</div>
          
        </div>
        <div class="prob-card draw">
          <div class="prob-header">
            <i class="fas fa-handshake"></i>
            <span>Draw</span>
          </div>
          <div class="prob-value">${m.prediction.probabilities.draw}%</div>
          
        </div>
        <div class="prob-card away">
          <div class="prob-header">
            <i class="fas fa-plane"></i>
            <span>AwayWin</span>
          </div>
          <div class="prob-value">${m.prediction.probabilities.away_win}%</div>
          
        </div>
      </div>
      
      <!-- Half-time scenarios -->
      ${m.prediction.ht_predictions ? `
        <div class="ht-section">
          <div class="ht-header">
            <i class="fas fa-clock"></i>
            <span>Half-Time Scenarios</span>
          </div>
          <div class="ht-cards">
            <div class="ht-card">
              <div class="ht-team">
                <i class="fas fa-home"></i>
                ${m.homeTeam.shortName || m.homeTeam.name.substring(0, 10)}
              </div>
              <div class="ht-prob">${m.prediction.ht_predictions.ht_home_win_ft_lose.probability}%</div>
              <div class="ht-label">HT Lead → FT Loss</div>
            </div>
            <div class="ht-card">
              <div class="ht-team">
                <i class="fas fa-plane"></i>
                ${m.awayTeam.shortName || m.awayTeam.name.substring(0, 10)}
              </div>
              <div class="ht-prob">${m.prediction.ht_predictions.ht_away_win_ft_lose.probability}%</div>
              <div class="ht-label">HT Lead → FT Loss</div>
            </div>
          </div>
        </div>
      ` : ''}
      
      <!-- Team stats and reasoning -->
      <div class="prediction-footer">
        ${teamStatsHtml}
        <div class="reasoning">
          <i class="fas fa-lightbulb"></i>
          <span>${m.prediction.reasoning}</span>
        </div>
        ${m.prediction.prediction_method === 'AI-Enhanced Multi-Source' || m.prediction.total_sources > 0 ? `
          <div class="explanation-button-container">
            <button class="btn btn-sm btn-info" onclick="showPredictionExplanation(${JSON.stringify(m.prediction).replace(/"/g, '&quot;')})">
              <i class="fas fa-info-circle"></i>
              Explain Prediction
            </button>
          </div>
        ` : ''}
      </div>
    </div>` : '';

  // Format match date better
  const matchDate = new Date(m.utcDate);
  const dateStr = matchDate.toLocaleDateString();
  const timeStr = matchDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  // Add local time for upcoming matches based on IP location
  const localTimeData = convertToLocalTime(m.utcDate);
  const isUpcomingMatch = m.status === 'SCHEDULED' || m.status === 'TIMED';
  const showLocalTime = isUpcomingMatch && userLocationData.loaded && localTimeData.time !== '--:--';
  
  // Create time display with local time if available
  let timeDisplayHtml = `
    <div class="match-time">${timeStr}</div>
    <div class="match-date">${dateStr}</div>
  `;
  
  if (showLocalTime) {
    const countryFlag = getCountryFlag(localTimeData.countryCode);
    const localTimeWithPeriod = localTimeData.period ? 
      `${localTimeData.time} ${localTimeData.period}` : 
      localTimeData.time;
      
    timeDisplayHtml = `
      <div class="match-time utc-time">${timeStr} UTC</div>
      <div class="match-time-local">
        <i class="fas fa-map-marker-alt"></i>
        ${localTimeWithPeriod} Local ${countryFlag}
      </div>
      <div class="match-date">${dateStr}</div>
    `;
  }

  return `
  <div class="match-card">
    <div class="match-header">
      <div class="match-status ${statusClass}">${m.statusDisplay}</div>
      <div class="match-time-container">
        ${timeDisplayHtml}
      </div>
    </div>
    <div class="match-teams">
      <div class="team home-team">
        <div class="team-indicator home-indicator">
          <i class="fas fa-home"></i>
          <span>HOME</span>
        </div>
        ${teamCrest(m.homeTeam.crest)}
        <div class="team-name">${m.homeTeam.name}</div>
        ${m.homeTeam.shortName && m.homeTeam.shortName !== m.homeTeam.name ? `<div class="team-short-name">${m.homeTeam.shortName}</div>` : ''}
      </div>
      <div class="vs-section">
        ${scoreHtml}
      </div>
      <div class="team away-team">
        <div class="team-indicator away-indicator">
          <i class="fas fa-plane"></i>
          <span>AWAY</span>
        </div>
        ${teamCrest(m.awayTeam.crest)}
        <div class="team-name">${m.awayTeam.name}</div>
        ${m.awayTeam.shortName && m.awayTeam.shortName !== m.awayTeam.name ? `<div class="team-short-name">${m.awayTeam.shortName}</div>` : ''}
      </div>
    </div>
    <div class="match-info">
      <div class="match-details">
        <div class="competition">
          ${m.competition.emblem ? `<img class="competition-emblem" src="${m.competition.emblem}" alt="emblem"/>` : ''}
          ${m.competition.area && m.competition.area.code ? `<span class="competition-country">${getCountryFlag(m.competition.area.code)} ${m.competition.area.code.toUpperCase()}</span>` : ''}
          <span>${m.competition.name}</span>
        </div>
        ${m.venue ? `<div class="venue"><i class="fas fa-map-marker-alt"></i> ${m.venue}</div>` : ''}
      </div>
      ${isFinished && m.score?.fullTime ? `
        <div class="match-result">
          <i class="fas fa-flag-checkered"></i>
          Full Time
        </div>` : ''}
    </div>
    ${liveEventsHtml}
    ${matchStatsHtml}
    ${matchEventsHtml}
    ${predictionHtml}
  </div>`;
}

// Helper function to get event icons
function getEventIcon(eventType) {
  const icons = {
    'goal': '<i class="fas fa-futbol" style="color: #00d4aa;"></i>',
    'yellow_card': '<i class="fas fa-square" style="color: #ffc107;"></i>',
    'red_card': '<i class="fas fa-square" style="color: #ff6b6b;"></i>',
    'substitution': '<i class="fas fa-exchange-alt" style="color: #667eea;"></i>',
    'penalty': '<i class="fas fa-dot-circle" style="color: #ff6b6b;"></i>',
    'corner': '<i class="fas fa-flag" style="color: #a0a9b8;"></i>'
  };
  return icons[eventType] || '<i class="fas fa-circle"></i>';
}

// Comparison rendering functions
function renderComparisonStats(statistics) {
  if (!statistics) return;
  
  // Update overall accuracy
  const overall = statistics.overall;
  $('overall-accuracy').textContent = `${overall.accuracy}%`;
  $('correct-predictions').textContent = overall.correct_predictions;
  $('total-predictions').textContent = overall.total_predictions;
  
  // Render confidence breakdown
  const confidenceContainer = $('confidence-breakdown');
  if (statistics.by_confidence && statistics.by_confidence.length > 0) {
    confidenceContainer.innerHTML = statistics.by_confidence.map(stat => `
      <div class="confidence-stat-card ${stat.confidence_bucket.toLowerCase()}">
        <div class="stat-header">
          <span class="confidence-level">${stat.confidence_bucket}</span>
          <span class="accuracy-badge">${stat.accuracy}%</span>
        </div>
        <div class="stat-details">
          <div class="stat-bar">
            <div class="stat-fill" style="width: ${stat.accuracy}%"></div>
          </div>
          <div class="stat-info">
            <span>${stat.correct_predictions}/${stat.total_predictions} correct</span>
            <span class="avg-confidence">Avg: ${stat.avg_confidence}%</span>
          </div>
        </div>
      </div>
    `).join('');
  } else {
    confidenceContainer.innerHTML = '<div class="no-data">No confidence data available</div>';
  }
  
  // Render outcome breakdown
  const outcomeContainer = $('outcome-breakdown');
  if (statistics.by_outcome && statistics.by_outcome.length > 0) {
    outcomeContainer.innerHTML = statistics.by_outcome.map(stat => {
      const outcomeLabel = stat.predicted_outcome === 'HOME_WIN' ? 'Home Wins' : 
                           stat.predicted_outcome === 'AWAY_WIN' ? 'Away Wins' : 'Draws';
      const outcomeIcon = stat.predicted_outcome === 'HOME_WIN' ? 'fa-home' : 
                         stat.predicted_outcome === 'AWAY_WIN' ? 'fa-plane' : 'fa-handshake';
      
      return `
        <div class="outcome-stat-card">
          <div class="stat-header">
            <i class="fas ${outcomeIcon}"></i>
            <span class="outcome-label">${outcomeLabel}</span>
            <span class="accuracy-badge">${stat.accuracy}%</span>
          </div>
          <div class="stat-details">
            <div class="stat-bar">
              <div class="stat-fill" style="width: ${stat.accuracy}%"></div>
            </div>
            <div class="stat-info">
              ${stat.correct_predictions}/${stat.total_predictions} correct
            </div>
          </div>
        </div>
      `;
    }).join('');
  } else {
    outcomeContainer.innerHTML = '<div class="no-data">No outcome data available</div>';
  }
}

function renderComparisonMatches(comparisons) {
  const container = $('comparison-matches');
  if (!comparisons || comparisons.length === 0) {
    container.innerHTML = `<div class=\"no-matches\"><i class=\"fas fa-info-circle\"></i>No comparison data available yet. Predictions will appear here after matches are finished.</div>`;
    return;
  }
  
  // Determine columns to remove incomplete last row
  const width = window.innerWidth || 1200;
  let cols = 1;
  if (width >= 1200) cols = 4; else if (width >= 992) cols = 3; else if (width >= 600) cols = 2; else cols = 1;
  const remainder = comparisons.length % cols;
  const trimmed = remainder === 0 ? comparisons : comparisons.slice(0, comparisons.length - remainder);
  
  // Store comparison data globally for modal access
  comparisonData = trimmed;
  
  container.innerHTML = trimmed.map((comparison, index) => comparisonCardHtml(comparison, index)).join('');
}

// Global array to store comparison data for modal access
let comparisonData = [];

function comparisonCardHtml(comparison, index) {
  const isCorrect = comparison.was_correct;
  const correctnessClass = isCorrect ? 'correct' : 'incorrect';
  const correctnessIcon = isCorrect ? 'fa-check-circle' : 'fa-times-circle';

  const truncateTeam = (name, maxLength = 12) => name.length > maxLength ? name.substring(0, maxLength) + '...' : name;

  const matchDate = new Date(comparison.match_date);
  const dateStr = matchDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const truncatedCompetition = comparison.competition.length > 15 ? comparison.competition.substring(0, 15) + '...' : comparison.competition;

  const featuredClass = '';
  
  const correctnessText = isCorrect ? 'CORRECT' : 'INCORRECT';
  const correctnessBg = isCorrect ? 'linear-gradient(135deg, #00d4aa, #00b894)' : 'linear-gradient(135deg, #ff6b6b, #ee5a52)';
  
  return `
    <div class="comparison-card-structured ${correctnessClass}" data-index="${index}" onclick="openComparisonModal(${index})">
      <div class="card-status-bar" style="background: ${correctnessBg}">
        <span class="status-text">${correctnessText}</span>
      </div>
      
      <div class="match-structure">
        <div class="team-section home-team">
          <div class="team-badge home-badge">
            <i class="fas fa-home"></i>
            <span>HOME</span>
          </div>
          <div class="team-crest">
            <i class="fas fa-shield-alt"></i>
          </div>
          <div class="team-name">${truncateTeam(comparison.home_team, 10)}</div>
          <div class="team-short">${truncateTeam(comparison.home_team, 6)}</div>
        </div>
        
        <div class="vs-section">
          <div class="vs-label">VS</div>
          <div class="confidence-badge">
            <i class="fas fa-brain"></i>
            <span>${comparison.prediction.confidence}%</span>
          </div>
        </div>
        
        <div class="team-section away-team">
          <div class="team-badge away-badge">
            <i class="fas fa-plane"></i>
            <span>AWAY</span>
          </div>
          <div class="team-crest">
            <i class="fas fa-shield-alt"></i>
          </div>
          <div class="team-name">${truncateTeam(comparison.away_team, 10)}</div>
          <div class="team-short">${truncateTeam(comparison.away_team, 6)}</div>
        </div>
      </div>
      
      <div class="match-info-bar">
        <div class="competition-badge">
          <i class="fas fa-trophy"></i>
          <span>${truncatedCompetition}</span>
        </div>
        <div class="time-info">
          <i class="fas fa-calendar"></i>
          <span class="match-date">${dateStr}</span>
        </div>
      </div>
    </div>`;
}

async function loadAllData(force = false) {
  try {
    setLoading(true);
    await loadCompetitions();

    const params = getFilterParams();

    // Parallel fetch for all tabs but only once
    const [liveRes, upcomingRes, predictionsRes, resultsRes, comparisonRes] = await Promise.all([
      fetchJson('/api/live-matches').catch(() => ({ success: false })),
      fetchJson('/api/upcoming-matches', params).catch(() => ({ success: false })),
      fetchJson('/api/predictions', params).catch(() => ({ success: false })),
      fetchJson('/api/results', params).catch(() => ({ success: false })),
      fetchJson('/api/comparison').catch(() => ({ success: false }))
    ]);

    if (liveRes.success) {
      cachedData.live = liveRes.data;
      $('live-count').textContent = liveRes.count || liveRes.data?.length || 0;
      if (currentTab === 'live') renderMatches(liveRes.data, 'live-matches');
    }

    if (upcomingRes.success) {
      cachedData.upcoming = upcomingRes.data;
      $('upcoming-count').textContent = upcomingRes.count || upcomingRes.data?.length || 0;
      if (currentTab === 'upcoming') renderMatches(upcomingRes.data, 'upcoming-matches');
    }

    if (predictionsRes.success) {
      // First populate the date dropdown with all available dates
      populateDateDropdown(predictionsRes.data);
      
      // Apply outcome and date filters for predictions
      const outcomeFilter = $('outcome-filter')?.value || '';
      const dateFilter = $('prediction-date')?.value || '';
      const filteredPredictions = filterPredictions(predictionsRes.data, outcomeFilter, dateFilter);
      
      cachedData.predictions = filteredPredictions;
      currentPredictions = filteredPredictions; // Store for batch saving/printing
      $('predictions-count').textContent = filteredPredictions.length;
      if (currentTab === 'predictions') {
        renderMatches(filteredPredictions, 'predictions-matches');
        // Enable save and print buttons if predictions are loaded
        const saveBtn = $('save-predictions-btn');
        const printBtn = $('print-predictions-btn');
        if (saveBtn) {
          saveBtn.disabled = filteredPredictions.length === 0;
        }
        if (printBtn) {
          printBtn.disabled = filteredPredictions.length === 0;
        }
      }
    }

    if (resultsRes.success) {
      cachedData.results = resultsRes.data;
      $('results-count').textContent = resultsRes.count || resultsRes.data?.length || 0;
      if (currentTab === 'results') renderMatches(resultsRes.data, 'results-matches');
    }

    if (comparisonRes.success) {
      cachedData.comparison = comparisonRes.data;
      $('comparison-count').textContent = comparisonRes.data?.comparisons?.length || 0;
      if (currentTab === 'comparison') {
        renderComparisonStats(comparisonRes.data.statistics);
        renderComparisonMatches(comparisonRes.data.comparisons);
      }
    }

    updateLastUpdated();
  } catch (e) {
    console.error(e);
    $('api-status').innerHTML = '<i class="fas fa-circle status-error"></i> API Error';
    showError(e.message);
  } finally {
    setLoading(false);
  }
}

// Prediction batch management functions
function showSaveBatchModal() {
  const saveModal = $('save-batch-modal');
  const predictionCount = $('prediction-count');
  const batchNameInput = $('batch-name-input');
  
  if (currentPredictions.length === 0) {
    showError('No predictions available to save. Please load predictions first.');
    return;
  }
  
  predictionCount.textContent = currentPredictions.length;
  
  // Create timestamp with date and time
  const now = new Date();
  const dateStr = now.toLocaleDateString();
  const timeStr = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  batchNameInput.value = `Predictions - ${dateStr} ${timeStr}`;
  saveModal.style.display = 'block';
}

function closeSaveBatchModal() {
  const saveModal = $('save-batch-modal');
  saveModal.style.display = 'none';
}

async function confirmSaveBatch() {
  const batchName = $('batch-name-input').value.trim();
  
  if (!batchName) {
    showError('Please enter a batch name.');
    return;
  }
  
  if (currentPredictions.length === 0) {
    showError('No predictions to save.');
    return;
  }
  
  try {
    setLoading(true);
    
    // Prepare prediction data for saving
    const predictionsData = currentPredictions.map(match => ({
      match: {
        id: match.id,
        homeTeam: match.homeTeam,
        awayTeam: match.awayTeam,
        competition: match.competition,
        utcDate: match.utcDate
      },
      prediction: match.prediction
    }));
    
    const response = await fetch('/api/save-prediction-batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        batch_name: batchName,
        predictions: predictionsData
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      closeSaveBatchModal();
      showSuccessMessage(result.message || 'Prediction batch saved successfully!');
      await loadPredictionBatches(); // Refresh batch list
    } else {
      showError(result.error || 'Failed to save prediction batch');
    }
  } catch (error) {
    showError('Error saving prediction batch: ' + error.message);
  } finally {
    setLoading(false);
  }
}

function showSuccessMessage(message) {
  // Simple success notification - you can enhance this with a proper success modal
  const notification = document.createElement('div');
  notification.className = 'success-notification';
  notification.innerHTML = `
    <div class="notification-content">
      <i class="fas fa-check-circle"></i>
      <span>${message}</span>
    </div>
  `;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: #00d4aa;
    color: white;
    padding: 15px 20px;
    border-radius: 5px;
    z-index: 1001;
    animation: slideIn 0.3s ease;
  `;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.remove();
  }, 3000);
}

async function loadPredictionBatches() {
  try {
    const response = await fetch('/api/prediction-batches');
    const result = await response.json();
    
    if (result.success) {
      availableBatches = result.data;
      populateBatchDropdown();
    }
  } catch (error) {
    console.error('Error loading prediction batches:', error);
  }
}

function populateBatchDropdown() {
  const batchSelector = $('batch-selector');
  if (!batchSelector) return;
  
  // Clear existing options except first
  while (batchSelector.options.length > 1) {
    batchSelector.remove(1);
  }
  
  // Add batch options
  availableBatches.forEach(batch => {
    const option = document.createElement('option');
    option.value = batch.id;
    option.textContent = `${batch.batch_name} (${batch.total_predictions} predictions)`;
    batchSelector.appendChild(option);
  });
}

async function loadBatchComparison() {
  const batchId = $('batch-selector').value;
  
  if (!batchId) {
    // Load regular comparison data
    await loadAllData(true);
    return;
  }
  
  try {
    setLoading(true);
    selectedBatchId = parseInt(batchId);
    
    const response = await fetch(`/api/batch-comparison/${batchId}`);
    const result = await response.json();
    
    if (result.success) {
      const comparisonData = result.data;
      
      // Render batch comparison statistics
      renderBatchStatistics(comparisonData.statistics);
      renderBatchComparisons(comparisonData.comparisons);
      
      // Update comparison count
      $('comparison-count').textContent = comparisonData.comparisons.length;
    } else {
      showError(result.error || 'Failed to load batch comparison');
    }
  } catch (error) {
    showError('Error loading batch comparison: ' + error.message);
  } finally {
    setLoading(false);
  }
}

function renderBatchStatistics(statistics) {
  // Update overall accuracy with batch data
  const winRatio = statistics.win_ratio || 0;
  $('overall-accuracy').textContent = `${winRatio}%`;
  $('correct-predictions').textContent = statistics.correct_predictions || 0;
  $('total-predictions').textContent = statistics.finished_matches || 0;
  
  // Clear confidence and outcome breakdowns for batch mode
  const confidenceContainer = $('confidence-breakdown');
  const outcomeContainer = $('outcome-breakdown');
  
  confidenceContainer.innerHTML = '<div class="batch-mode-notice"><i class="fas fa-info-circle"></i> Batch comparison mode - showing win ratio for selected prediction batch</div>';
  outcomeContainer.innerHTML = `
    <div class="batch-stats">
      <div class="batch-stat-item">
        <span class="stat-label">Total Predictions:</span>
        <span class="stat-value">${statistics.total_predictions}</span>
      </div>
      <div class="batch-stat-item">
        <span class="stat-label">Matches Finished:</span>
        <span class="stat-value">${statistics.finished_matches}</span>
      </div>
      <div class="batch-stat-item">
        <span class="stat-label">Correct Predictions:</span>
        <span class="stat-value">${statistics.correct_predictions}</span>
      </div>
      <div class="batch-stat-item win-ratio">
        <span class="stat-label">Win Ratio:</span>
        <span class="stat-value">${winRatio}%</span>
      </div>
    </div>
  `;
}

function renderBatchComparisons(comparisons) {
  const container = $('comparison-matches');
  if (!comparisons || comparisons.length === 0) {
    container.innerHTML = `<div class=\"no-matches\"><i class=\"fas fa-info-circle\"></i>No comparison data available for this batch.</div>`;
    return;
  }
  
  // Determine columns to remove incomplete last row
  const width = window.innerWidth || 1200;
  let cols = 1;
  if (width >= 1200) cols = 4; else if (width >= 992) cols = 3; else if (width >= 600) cols = 2; else cols = 1;
  const remainder = comparisons.length % cols;
  const trimmed = remainder === 0 ? comparisons : comparisons.slice(0, comparisons.length - remainder);
  
  // Store comparison data globally for modal access
  comparisonData = trimmed;
  
  container.innerHTML = trimmed.map((comparison, index) => batchComparisonCardHtml(comparison, index)).join('');
}

function batchComparisonCardHtml(comparison, index) {
  const isCorrect = comparison.was_correct;
  const correctnessClass = isCorrect === null ? 'pending' : (isCorrect ? 'correct' : 'incorrect');
  const correctnessIcon = isCorrect === null ? 'fa-clock' : (isCorrect ? 'fa-check-circle' : 'fa-times-circle');

  const truncateTeam = (name, maxLength = 12) => name.length > maxLength ? name.substring(0, maxLength) + '...' : name;

  const matchDate = new Date(comparison.match_date);
  const dateStr = matchDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const truncatedCompetition = comparison.competition.length > 15 ? comparison.competition.substring(0, 15) + '...' : comparison.competition;

  const featuredClass = '';
  
  const correctnessText = isCorrect === null ? 'PENDING' : (isCorrect ? 'CORRECT' : 'INCORRECT');
  const correctnessBg = isCorrect === null ? 'linear-gradient(135deg, #ffc107, #ffb300)' : 
                       (isCorrect ? 'linear-gradient(135deg, #00d4aa, #00b894)' : 'linear-gradient(135deg, #ff6b6b, #ee5a52)');
  
  return `
    <div class="comparison-card-structured ${correctnessClass}" data-index="${index}" onclick="openComparisonModal(${index})">
      <div class="card-status-bar" style="background: ${correctnessBg}">
        <span class="status-text">${correctnessText}</span>
      </div>
      
      <div class="match-structure">
        <div class="team-section home-team">
          <div class="team-badge home-badge">
            <i class="fas fa-home"></i>
            <span>HOME</span>
          </div>
          <div class="team-crest">
            <i class="fas fa-shield-alt"></i>
          </div>
          <div class="team-name">${truncateTeam(comparison.home_team, 10)}</div>
          <div class="team-short">${truncateTeam(comparison.home_team, 6)}</div>
        </div>
        
        <div class="vs-section">
          <div class="vs-label">VS</div>
          <div class="confidence-badge">
            <i class="fas fa-brain"></i>
            <span>${comparison.prediction.confidence}%</span>
          </div>
        </div>
        
        <div class="team-section away-team">
          <div class="team-badge away-badge">
            <i class="fas fa-plane"></i>
            <span>AWAY</span>
          </div>
          <div class="team-crest">
            <i class="fas fa-shield-alt"></i>
          </div>
          <div class="team-name">${truncateTeam(comparison.away_team, 10)}</div>
          <div class="team-short">${truncateTeam(comparison.away_team, 6)}</div>
        </div>
      </div>
      
      <div class="match-info-bar">
        <div class="competition-badge">
          <i class="fas fa-trophy"></i>
          <span>${truncatedCompetition}</span>
        </div>
        <div class="time-info">
          <i class="fas fa-calendar"></i>
          <span class="match-date">${dateStr}</span>
        </div>
      </div>
    </div>`;
}

// Batch Deletion Functions
let batchToDelete = null;

function showDeleteBatchModal() {
  const batchSelector = $('batch-selector');
  const selectedBatchId = batchSelector.value;
  
  if (!selectedBatchId || selectedBatchId === '') {
    showError('Please select a batch to delete.');
    return;
  }
  
  // Find the selected batch info
  const selectedBatch = availableBatches.find(batch => batch.id == selectedBatchId);
  if (!selectedBatch) {
    showError('Selected batch not found.');
    return;
  }
  
  // Store batch info for deletion
  batchToDelete = selectedBatch;
  
  // Show confirmation modal
  const deleteModal = $('delete-batch-modal');
  const batchNameSpan = $('delete-batch-name');
  
  batchNameSpan.textContent = selectedBatch.batch_name;
  deleteModal.style.display = 'block';
}

function closeDeleteBatchModal() {
  const deleteModal = $('delete-batch-modal');
  deleteModal.style.display = 'none';
  batchToDelete = null;
}

async function confirmDeleteBatch() {
  if (!batchToDelete) {
    showError('No batch selected for deletion.');
    return;
  }
  
  try {
    setLoading(true);
    
    const response = await fetch(`/api/delete-prediction-batch/${batchToDelete.id}`, {
      method: 'DELETE'
    });
    
    const result = await response.json();
    
    if (result.success) {
      closeDeleteBatchModal();
      showSuccessMessage(result.message || 'Prediction batch deleted successfully!');
      
      // Reset batch selector to current data
      const batchSelector = $('batch-selector');
      batchSelector.value = '';
      
      // Disable buttons
      const loadBtn = $('load-batch-btn');
      const deleteBtn = $('delete-batch-btn');
      if (loadBtn) loadBtn.disabled = true;
      if (deleteBtn) deleteBtn.disabled = true;
      
      // Refresh batch list and reload current comparison
      await loadPredictionBatches();
      await loadAllData(true); // Reload current live data comparison
    } else {
      showError(result.error || 'Failed to delete prediction batch');
    }
  } catch (error) {
    showError('Error deleting prediction batch: ' + error.message);
  } finally {
    setLoading(false);
  }
}

// Detailed Comparison Modal Functions
function openComparisonModal(index) {
  const modal = $('comparison-details-modal');
  const comparison = comparisonData[index];
  if (!comparison) return;
  populateComparisonModal(comparison);
  modal.style.display = 'block';
}

function showComparisonDetails(comparison) {
  // Backward compatibility if called with object
  const modal = $('comparison-details-modal');
  if (!comparison) return;
  if (typeof comparison === 'string') {
    try { comparison = JSON.parse(decodeURIComponent(comparison)); } catch(e) { return; }
  }
  populateComparisonModal(comparison);
  modal.style.display = 'block';
}

function closeComparisonDetailsModal() {
  const modal = $('comparison-details-modal');
  modal.style.display = 'none';
}

function populateComparisonModal(comparison) {
  // Safety: if encoded string slipped through
  if (typeof comparison === 'string') {
    try { comparison = JSON.parse(decodeURIComponent(comparison)); } catch(e) { return; }
  }
  
  try {
    // Determine correctness state
  const isCorrect = comparison.was_correct;
  const correctnessClass = isCorrect === null ? 'pending' : (isCorrect ? 'correct' : 'incorrect');
  const correctnessIcon = isCorrect === null ? 'fa-clock' : (isCorrect ? 'fa-check-circle' : 'fa-times-circle');
  const correctnessText = isCorrect === null ? 'Pending' : (isCorrect ? 'Correct' : 'Incorrect');
  
  // Format match date
  const matchDate = new Date(comparison.match_date);
  const dateStr = matchDate.toLocaleDateString();
  const timeStr = matchDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  // Populate teams header
  const teamsElement = $('modal-match-teams');
  teamsElement.innerHTML = `
    <span class="home-team">${comparison.home_team}</span>
    <span class="vs">vs</span>
    <span class="away-team">${comparison.away_team}</span>
  `;
  
  // Populate correctness indicator
  const correctnessElement = $('modal-correctness-indicator');
  correctnessElement.className = `correctness-indicator ${correctnessClass}`;
  correctnessElement.innerHTML = `
    <i class="fas ${correctnessIcon}"></i>
    <span>${correctnessText}</span>
  `;
  
  // Populate prediction details
  const predictionText = comparison.prediction.predicted_team === 'Draw' ? 
    'Draw' : `${comparison.prediction.predicted_team} to Win`;
  
  const predictionDetailsElement = $('modal-prediction-details');
  predictionDetailsElement.innerHTML = `
    <div class="predicted-outcome">
      <span class="prediction-text">${predictionText}</span>
      <span class="confidence ${comparison.prediction.confidence >= 70 ? 'high-confidence' : 'medium-confidence'}">
        ${comparison.prediction.confidence}% confidence
      </span>
    </div>
    <div class="prediction-probabilities">
      <div class="prob-item">
        <span class="prob-label">Home Win</span>
        <div class="prob-bar">
          <div class="prob-fill" style="width: ${comparison.prediction.probabilities.home_win}%"></div>
        </div>
        <span class="prob-value">${comparison.prediction.probabilities.home_win}%</span>
      </div>
      <div class="prob-item">
        <span class="prob-label">Draw</span>
        <div class="prob-bar">
          <div class="prob-fill" style="width: ${comparison.prediction.probabilities.draw}%"></div>
        </div>
        <span class="prob-value">${comparison.prediction.probabilities.draw}%</span>
      </div>
      <div class="prob-item">
        <span class="prob-label">Away Win</span>
        <div class="prob-bar">
          <div class="prob-fill" style="width: ${comparison.prediction.probabilities.away_win}%"></div>
        </div>
        <span class="prob-value">${comparison.prediction.probabilities.away_win}%</span>
      </div>
    </div>
    ${comparison.prediction.reasoning ? `
      <div class="modal-prediction-reasoning">
        <i class="fas fa-lightbulb"></i>
        ${comparison.prediction.reasoning}
      </div>
    ` : ''}
    ${comparison.prediction.probabilities && (comparison.prediction.probabilities.ht_home_win_ft_lose || comparison.prediction.probabilities.ht_away_win_ft_lose) ? `
      <div class="ht-predictions-summary">
        <h6><i class="fas fa-clock"></i> Half-Time Scenarios</h6>
        <div class="ht-summary-grid">
          <div class="ht-summary-item">
            <span class="ht-label">${comparison.home_team} HT Lead → FT Loss:</span>
            <span class="ht-value">${comparison.prediction.probabilities.ht_home_win_ft_lose}%</span>
          </div>
          <div class="ht-summary-item">
            <span class="ht-label">${comparison.away_team} HT Lead → FT Loss:</span>
            <span class="ht-value">${comparison.prediction.probabilities.ht_away_win_ft_lose}%</span>
          </div>
        </div>
      </div>
    ` : ''}
  `;
  
  // Populate result details
  const resultDetailsElement = $('modal-result-details');
  if (comparison.result) {
    const result = comparison.result;
    const resultText = result.actual_outcome === 'HOME_WIN' ? 
      `${comparison.home_team} Won` :
      result.actual_outcome === 'AWAY_WIN' ? 
      `${comparison.away_team} Won` :
      'Draw';
    
    resultDetailsElement.innerHTML = `
      <div class="final-score">
        <span class="home-score">${comparison.home_team} ${result.home_score}</span>
        <span class="score-separator">-</span>
        <span class="away-score">${result.away_score} ${comparison.away_team}</span>
      </div>
      <div class="result-text">${resultText}</div>
    `;
  } else {
    resultDetailsElement.innerHTML = `
      <div class="pending-result">
        <i class="fas fa-clock"></i>
        Match not yet finished
      </div>
    `;
  }
  
  // Populate match details
  const matchDetailsElement = $('modal-match-details');
  matchDetailsElement.innerHTML = `
    <div class="match-detail-item">
      <span class="detail-label"><i class="fas fa-trophy"></i> Competition:</span>
      <span class="detail-value">${comparison.competition}</span>
    </div>
    <div class="match-detail-item">
      <span class="detail-label"><i class="fas fa-calendar-alt"></i> Date:</span>
      <span class="detail-value">${dateStr}</span>
    </div>
    <div class="match-detail-item">
      <span class="detail-label"><i class="fas fa-clock"></i> Time:</span>
      <span class="detail-value">${timeStr}</span>
    </div>
  `;
  
  } catch (error) {
    // Silent fail for modal population errors
  }
}

// Settings Management Functions
function loadUserSettings() {
  const savedSettings = localStorage.getItem('footballDashboardSettings');
  if (savedSettings) {
    try {
      userSettings = {...userSettings, ...JSON.parse(savedSettings)};
    } catch (e) {
      console.error('Error loading settings:', e);
    }
  }
  applyUserSettings();
}

function saveUserSettings() {
  try {
    localStorage.setItem('footballDashboardSettings', JSON.stringify(userSettings));
  } catch (e) {
    console.error('Error saving settings:', e);
  }
}

function applyUserSettings() {
  // Update UI elements
  const refreshSlider = $('refresh-rate-slider');
  const autoRefreshToggle = $('auto-refresh-toggle');
  const animationsToggle = $('show-animations-toggle');
  const compactModeToggle = $('compact-mode-toggle');
  
  if (refreshSlider) {
    refreshSlider.value = userSettings.refreshInterval;
    updateRefreshDisplay(userSettings.refreshInterval);
  }
  
  if (autoRefreshToggle) {
    autoRefreshToggle.checked = userSettings.autoRefreshEnabled;
  }
  
  if (animationsToggle) {
    animationsToggle.checked = userSettings.animationsEnabled;
  }
  
  if (compactModeToggle) {
    compactModeToggle.checked = userSettings.compactMode;
  }
  
  // Apply visual settings
  document.body.classList.toggle('no-animations', !userSettings.animationsEnabled);
  document.body.classList.toggle('compact-mode', userSettings.compactMode);
  
  // Restart auto refresh with new settings
  startAutoRefresh();
}

function updateRefreshDisplay(seconds) {
  const display = $('refresh-rate-display');
  if (!display) return;
  
  if (seconds < 60) {
    display.textContent = `${seconds} seconds`;
  } else {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    if (remainingSeconds === 0) {
      display.textContent = `${minutes} minute${minutes === 1 ? '' : 's'}`;
    } else {
      display.textContent = `${minutes}m ${remainingSeconds}s`;
    }
  }
}

function initializeSettingsTab() {
  // Refresh rate slider
  const refreshSlider = $('refresh-rate-slider');
  if (refreshSlider) {
    refreshSlider.addEventListener('input', (e) => {
      const value = parseInt(e.target.value);
      userSettings.refreshInterval = value;
      updateRefreshDisplay(value);
      saveUserSettings();
      startAutoRefresh(); // Restart with new interval
    });
  }
  
  // Auto refresh toggle
  const autoRefreshToggle = $('auto-refresh-toggle');
  if (autoRefreshToggle) {
    autoRefreshToggle.addEventListener('change', (e) => {
      userSettings.autoRefreshEnabled = e.target.checked;
      saveUserSettings();
      startAutoRefresh(); // Apply immediately
    });
  }
  
  // Animations toggle
  const animationsToggle = $('show-animations-toggle');
  if (animationsToggle) {
    animationsToggle.addEventListener('change', (e) => {
      userSettings.animationsEnabled = e.target.checked;
      document.body.classList.toggle('no-animations', !e.target.checked);
      saveUserSettings();
    });
  }
  
  // Compact mode toggle
  const compactModeToggle = $('compact-mode-toggle');
  if (compactModeToggle) {
    compactModeToggle.addEventListener('change', (e) => {
      userSettings.compactMode = e.target.checked;
      document.body.classList.toggle('compact-mode', e.target.checked);
      saveUserSettings();
    });
  }
}

// Old bind function removed - now using inline onclick for simplicity

// Make functions globally accessible
window.showComparisonDetails = showComparisonDetails;
window.closeComparisonDetailsModal = closeComparisonDetailsModal;
window.openComparisonModal = openComparisonModal;

// Test function to verify modal works
window.testModal = function() {
  const modal = document.getElementById('comparison-details-modal');
  if (modal) {
    modal.style.display = 'block';
    console.log('Modal test: opened');
  } else {
    console.error('Modal test: modal not found');
  }
};

// Debug function to show current comparison data
window.debugComparisons = function() {
  console.log('comparisonData:', comparisonData);
  console.log('comparisonData length:', comparisonData.length);
};

// Close modal when clicking outside content
window.addEventListener('click', (evt) => {
  const modal = $('comparison-details-modal');
  if (evt.target === modal) {
    closeComparisonDetailsModal();
  }
});

// ESC closes modal
window.addEventListener('keydown', (evt) => {
  if (evt.key === 'Escape') closeComparisonDetailsModal();
});

// As a safety net, delegate clicks for mini comparison cards
// This ensures clicks work even if inline onclick fails due to caching or CSP
document.addEventListener('click', (evt) => {
  const card = evt.target.closest('.comparison-card-structured, .comparison-card-mini');
  if (card) {
    const idx = parseInt(card.getAttribute('data-index'), 10);
    if (!Number.isNaN(idx)) openComparisonModal(idx);
  }
});

// ========== IP LOCATION DATA FETCHING ==========

// Fetch user's IP location data for time conversion
async function fetchUserLocationData() {
  try {
    console.log('Fetching user location data for time conversion...');
    const response = await fetchJson('/api/ip-location');
    
    if (response.success && response.data) {
      userLocationData = {
        timezone: response.data.timezone || 'UTC',
        country_code: response.data.country_code || 'XX',
        city: response.data.city || 'Unknown',
        country: response.data.country || 'Unknown',
        loaded: true
      };
      console.log('User location data loaded:', userLocationData);
    } else {
      // Fallback to browser timezone
      console.warn('IP location failed, using browser timezone');
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      userLocationData = {
        timezone: timezone,
        country_code: 'XX',
        city: 'Unknown',
        country: 'Unknown', 
        loaded: true
      };
    }
  } catch (error) {
    console.error('Failed to fetch location data:', error);
    // Fallback to browser timezone
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    userLocationData = {
      timezone: timezone,
      country_code: 'XX',
      city: 'Unknown',
      country: 'Unknown',
      loaded: true
    };
  }
}

// Convert UTC time to user's local time
function convertToLocalTime(utcTimeString) {
  if (!userLocationData.loaded || !utcTimeString) {
    return { time: '--:--', period: '', countryCode: 'XX' };
  }
  
  try {
    const utcDate = new Date(utcTimeString);
    const localDate = new Date(utcDate.toLocaleString("en-US", {
      timeZone: userLocationData.timezone
    }));
    
    let hours = localDate.getHours();
    const minutes = String(localDate.getMinutes()).padStart(2, '0');
    let period = '';
    
    // Format based on current time format preference
    const currentFormat = localStorage.getItem('timeFormat') || '12';
    
    if (currentFormat === '12') {
      period = hours >= 12 ? 'PM' : 'AM';
      hours = hours % 12 || 12;
    } else {
      hours = String(hours).padStart(2, '0');
    }
    
    return {
      time: `${hours}:${minutes}`,
      period: period,
      countryCode: userLocationData.country_code
    };
  } catch (error) {
    console.error('Time conversion failed:', error);
    return { time: '--:--', period: '', countryCode: 'XX' };
  }
}

// ========== TIME DISPLAY FUNCTIONALITY ==========

// Global variables for time display
let timeUpdateInterval = null;
let timeFormat = '12'; // '12' or '24'

// Time display functions
function initializeTimeDisplay() {
  console.log('Initializing time display...');
  
  // Initialize time format buttons
  const format12Btn = $('format-12h');
  const format24Btn = $('format-24h');
  
  if (format12Btn && format24Btn) {
    format12Btn.addEventListener('click', () => setTimeFormat('12'));
    format24Btn.addEventListener('click', () => setTimeFormat('24'));
  }
  
  // Load saved time format preference
  const savedFormat = localStorage.getItem('timeFormat') || '12';
  setTimeFormat(savedFormat);
  
  // Start time update loop
  startTimeUpdate();
  
  // Get timezone and location information
  updateTimezoneInfo();
}

function setTimeFormat(format) {
  timeFormat = format;
  localStorage.setItem('timeFormat', format);
  
  // Update button states
  const format12Btn = $('format-12h');
  const format24Btn = $('format-24h');
  
  if (format12Btn && format24Btn) {
    format12Btn.classList.toggle('active', format === '12');
    format24Btn.classList.toggle('active', format === '24');
  }
  
  // Update display immediately
  updateTimeDisplay();
}

function startTimeUpdate() {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
  }
  
  // Update immediately
  updateTimeDisplay();
  
  // Update every second
  timeUpdateInterval = setInterval(updateTimeDisplay, 1000);
}

function updateTimeDisplay() {
  const now = new Date();
  
  // Update main time display
  updateMainTime(now);
  
  // Update tab indicator
  updateTabTimeIndicator(now);
  
  // Update UTC time
  updateUTCTime(now);
  
  // Update world clocks
  updateWorldClocks(now);
  
  // Update date display
  updateDateDisplay(now);
}

function updateMainTime(date) {
  const hoursElement = $('hours');
  const minutesElement = $('minutes');
  const secondsElement = $('seconds');
  const periodElement = $('period');
  
  if (!hoursElement || !minutesElement || !secondsElement) return;
  
  let hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  if (timeFormat === '12') {
    const period = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    
    if (periodElement) {
      periodElement.textContent = period;
      periodElement.style.display = 'inline';
    }
  } else {
    hours = String(hours).padStart(2, '0');
    
    if (periodElement) {
      periodElement.style.display = 'none';
    }
  }
  
  hoursElement.textContent = String(hours).padStart(2, '0');
  minutesElement.textContent = minutes;
  secondsElement.textContent = seconds;
}

function updateTabTimeIndicator(date) {
  const indicator = $('time-indicator');
  if (!indicator) return;
  
  let hours = date.getHours();
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  if (timeFormat === '12') {
    const period = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    indicator.textContent = `${String(hours).padStart(2, '0')}:${minutes}:${seconds} ${period}`;
  } else {
    hours = String(hours).padStart(2, '0');
    indicator.textContent = `${hours}:${minutes}:${seconds}`;
  }
}

function updateUTCTime(date) {
  const utcTimeElement = $('utc-time');
  if (!utcTimeElement) return;
  
  const utcHours = String(date.getUTCHours()).padStart(2, '0');
  const utcMinutes = String(date.getUTCMinutes()).padStart(2, '0');
  const utcSeconds = String(date.getUTCSeconds()).padStart(2, '0');
  
  utcTimeElement.textContent = `${utcHours}:${utcMinutes}:${utcSeconds}`;
}

function updateWorldClocks(date) {
  // Define world timezones
  const worldTimezones = {
    'ny': { timezone: 'America/New_York', name: 'New York' },
    'london': { timezone: 'Europe/London', name: 'London' },
    'tokyo': { timezone: 'Asia/Tokyo', name: 'Tokyo' },
    'sydney': { timezone: 'Australia/Sydney', name: 'Sydney' }
  };
  
  Object.entries(worldTimezones).forEach(([key, {timezone}]) => {
    const timeElement = $(key + '-time');
    const dateElement = $(key + '-date');
    
    if (timeElement) {
      try {
        const zonedDate = new Date(date.toLocaleString("en-US", {timeZone: timezone}));
        
        let hours = zonedDate.getHours();
        const minutes = String(zonedDate.getMinutes()).padStart(2, '0');
        const seconds = String(zonedDate.getSeconds()).padStart(2, '0');
        
        if (timeFormat === '12') {
          const period = hours >= 12 ? 'PM' : 'AM';
          hours = hours % 12 || 12;
          timeElement.textContent = `${String(hours).padStart(2, '0')}:${minutes}:${seconds} ${period}`;
        } else {
          hours = String(hours).padStart(2, '0');
          timeElement.textContent = `${hours}:${minutes}:${seconds}`;
        }
        
        if (dateElement) {
          const options = { month: 'short', day: 'numeric', timeZone: timezone };
          dateElement.textContent = zonedDate.toLocaleDateString('en-US', options);
        }
      } catch (error) {
        console.warn(`Error updating time for ${timezone}:`, error);
        timeElement.textContent = '--:--:--';
        if (dateElement) dateElement.textContent = '--';
      }
    }
  });
}

function updateDateDisplay(date) {
  const dateElement = $('date-display');
  if (!dateElement) return;
  
  const options = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  };
  
  dateElement.textContent = date.toLocaleDateString('en-US', options);
}

function updateTimezoneInfo() {
  try {
    // Get timezone information
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const now = new Date();
    
    // Update timezone name
    const timezoneNameElement = $('timezone-name');
    if (timezoneNameElement) {
      // Format timezone name nicely (e.g., "America/New_York" -> "New York")
      const formattedTimezone = timezone.replace(/_/g, ' ').split('/').pop();
      timezoneNameElement.textContent = formattedTimezone;
    }
    
    // Update timezone offset
    const timezoneOffsetElement = $('timezone-offset');
    if (timezoneOffsetElement) {
      const offsetMinutes = now.getTimezoneOffset();
      const offsetHours = Math.floor(Math.abs(offsetMinutes) / 60);
      const offsetMins = Math.abs(offsetMinutes) % 60;
      const offsetSign = offsetMinutes <= 0 ? '+' : '-';
      
      let offsetText = `UTC${offsetSign}${offsetHours}`;
      if (offsetMins > 0) {
        offsetText += `:${String(offsetMins).padStart(2, '0')}`;
      }
      
      timezoneOffsetElement.textContent = offsetText;
    }
    
    // Try to detect location (basic approach)
    detectLocation();
    
  } catch (error) {
    console.warn('Error updating timezone info:', error);
  }
}

async function detectLocation() {
  const locationNameElement = $('location-name');
  const locationCountryElement = $('location-country');
  
  if (!locationNameElement || !locationCountryElement) return;
  
  try {
    // Use IP-based location detection
    const response = await fetchJson('/api/ip-location');
    
    if (response.success && response.data) {
      const data = response.data;
      const countryFlag = getCountryFlag(data.country_code);
      
      // Display city with country prefix
      locationNameElement.textContent = data.city || 'Unknown';
      locationCountryElement.innerHTML = `${countryFlag} ${data.country || 'Unknown'} (${data.country_code || 'XX'})`;
      
      // Update IP info if available
      const ipInfoElement = $('ip-info');
      if (ipInfoElement) {
        ipInfoElement.textContent = `IP: ${data.ip || 'Unknown'}`;
      }
      
      // Store location data for other components
      window.detectedLocation = {
        city: data.city,
        country: data.country,
        country_code: data.country_code,
        timezone: data.timezone,
        ip: data.ip
      };
      
      console.log('IP-based location detected:', window.detectedLocation);
      
    } else {
      // Fallback to timezone-based detection
      console.warn('IP location detection failed, using timezone fallback:', response.error);
      
      const fallbackData = response.fallback || {};
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
      
      // Use timezone to guess location
      const timezoneLocationMap = {
        'America/New_York': { city: 'New York', country: 'United States', code: 'US' },
        'America/Chicago': { city: 'Chicago', country: 'United States', code: 'US' },
        'America/Denver': { city: 'Denver', country: 'United States', code: 'US' },
        'America/Los_Angeles': { city: 'Los Angeles', country: 'United States', code: 'US' },
        'Europe/London': { city: 'London', country: 'United Kingdom', code: 'GB' },
        'Europe/Paris': { city: 'Paris', country: 'France', code: 'FR' },
        'Europe/Berlin': { city: 'Berlin', country: 'Germany', code: 'DE' },
        'Europe/Rome': { city: 'Rome', country: 'Italy', code: 'IT' },
        'Europe/Madrid': { city: 'Madrid', country: 'Spain', code: 'ES' },
        'Asia/Tokyo': { city: 'Tokyo', country: 'Japan', code: 'JP' },
        'Asia/Shanghai': { city: 'Shanghai', country: 'China', code: 'CN' },
        'Asia/Dubai': { city: 'Dubai', country: 'United Arab Emirates', code: 'AE' },
        'Australia/Sydney': { city: 'Sydney', country: 'Australia', code: 'AU' },
        'Australia/Melbourne': { city: 'Melbourne', country: 'Australia', code: 'AU' }
      };
      
      const location = timezoneLocationMap[timezone];
      if (location) {
        const countryFlag = getCountryFlag(location.code);
        locationNameElement.textContent = location.city;
        locationCountryElement.innerHTML = `${countryFlag} ${location.country} (${location.code})`;
      } else {
        // Ultimate fallback: extract from timezone
        const parts = timezone.split('/');
        const city = parts[parts.length - 1].replace(/_/g, ' ');
        const region = parts[0].replace(/_/g, ' ');
        
        locationNameElement.textContent = city;
        locationCountryElement.innerHTML = `🌍 ${region} (XX)`;
      }
      
      const ipInfoElement = $('ip-info');
      if (ipInfoElement) {
        ipInfoElement.textContent = fallbackData.ip ? `IP: ${fallbackData.ip}` : 'IP: Unknown';
      }
    }
    
  } catch (error) {
    console.error('Location detection failed:', error);
    
    // Fallback to basic timezone detection
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const parts = timezone.split('/');
    const city = parts[parts.length - 1].replace(/_/g, ' ');
    const region = parts[0].replace(/_/g, ' ');
    
    locationNameElement.textContent = city;
    locationCountryElement.innerHTML = `🌍 ${region} (XX)`;
    
    const ipInfoElement = $('ip-info');
    if (ipInfoElement) {
      ipInfoElement.textContent = 'IP: Unknown';
    }
  }
}

// Function to get country flag emoji
function getCountryFlag(countryCode) {
  if (!countryCode || countryCode === 'XX') return '🌍';
  
  // Convert country code to flag emoji
  const codePoints = countryCode
    .toUpperCase()
    .split('')
    .map(char => 127397 + char.charCodeAt(0));
  
  return String.fromCodePoint(...codePoints);
}

// Clean up time interval when leaving time tab or page
function cleanupTimeDisplay() {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
    timeUpdateInterval = null;
  }
}

// ========== END TIME DISPLAY FUNCTIONALITY ==========

// ========== AUTHENTICATION FUNCTIONALITY ==========

// Authentication functions
async function checkAuthStatus() {
  try {
    const response = await fetchJson('/api/auth/user');
    if (response.success) {
      isAuthenticated = response.authenticated;
      currentUser = response.user;
      ipUsage = response.ip_usage;
      
      updateAuthUI();
      updateUsageDisplay();
    }
  } catch (error) {
    console.error('Error checking auth status:', error);
  }
}

function updateAuthUI() {
  const authButtons = $('auth-buttons');
  const userInfo = $('user-info');
  const usernameDisplay = $('username-display');
  
  if (isAuthenticated && currentUser) {
    authButtons.style.display = 'none';
    userInfo.style.display = 'flex';
    usernameDisplay.textContent = currentUser.username;
  } else {
    authButtons.style.display = 'flex';
    userInfo.style.display = 'none';
  }
}

function updateUsageDisplay() {
  const usageDisplay = $('usage-display');
  const usageInfo = $('usage-info');
  
  if (isAuthenticated) {
    usageInfo.style.display = 'none';
  } else {
    usageInfo.style.display = 'block';
    if (ipUsage.limit_exceeded) {
      usageDisplay.innerHTML = `<span class="usage-exceeded"><i class="fas fa-exclamation-triangle"></i> Usage limit exceeded</span>`;
    } else {
      usageDisplay.textContent = `${ipUsage.remaining_requests}/5 requests remaining`;
    }
  }
}

// Show authentication modals
function showSignInModal() {
  const modal = $('signin-modal');
  const input = $('signin-username');
  input.value = '';
  modal.style.display = 'block';
  input.focus();
}

function showSignUpModal() {
  const modal = $('signup-modal');
  const input = $('signup-username');
  input.value = '';
  modal.style.display = 'block';
  input.focus();
}

function closeAuthModals() {
  const signinModal = $('signin-modal');
  const signupModal = $('signup-modal');
  signinModal.style.display = 'none';
  signupModal.style.display = 'none';
}

// Authentication API calls
async function confirmSignIn() {
  const username = $('signin-username').value.trim();
  
  if (!username) {
    showError('Please enter your username.');
    return;
  }
  
  try {
    setLoading(true);
    
    const response = await fetch('/api/auth/signin', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    });
    
    const result = await response.json();
    
    if (result.success) {
      closeAuthModals();
      showSuccessMessage(result.message);
      await checkAuthStatus();
      // After successful sign-in, reload all data with full access
      await loadAllData(true);
      startAutoRefresh();
    } else {
      showError(result.error);
    }
  } catch (error) {
    showError('Sign in failed: ' + error.message);
  } finally {
    setLoading(false);
  }
}

async function confirmSignUp() {
  const username = $('signup-username').value.trim();
  
  if (!username) {
    showError('Please enter a username.');
    return;
  }
  
  if (username.length < 3 || username.length > 20) {
    showError('Username must be between 3 and 20 characters long.');
    return;
  }
  
  if (!/^[a-zA-Z0-9_-]+$/.test(username)) {
    showError('Username can only contain letters, numbers, hyphens, and underscores.');
    return;
  }
  
  try {
    setLoading(true);
    
    const response = await fetch('/api/auth/signup', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ username })
    });
    
    const result = await response.json();
    
    if (result.success) {
      closeAuthModals();
      showSuccessMessage(result.message);
      await checkAuthStatus();
      // After successful sign-up, reload all data with full access
      await loadAllData(true);
      startAutoRefresh();
    } else {
      showError(result.error);
    }
  } catch (error) {
    showError('Sign up failed: ' + error.message);
  } finally {
    setLoading(false);
  }
}

async function confirmLogout() {
  try {
    setLoading(true);
    
    const response = await fetch('/api/auth/logout', {
      method: 'POST'
    });
    
    const result = await response.json();
    
    if (result.success) {
      showSuccessMessage(result.message);
      isAuthenticated = false;
      currentUser = null;
      updateAuthUI();
      await checkAuthStatus();
    } else {
      showError(result.error);
    }
  } catch (error) {
    showError('Logout failed: ' + error.message);
  } finally {
    setLoading(false);
  }
}

// Enhanced fetchJson to handle IP limits and authentication
const originalFetchJson = fetchJson;
fetchJson = async function(url, params = {}) {
  try {
    const result = await originalFetchJson(url, params);
    
    // Update IP usage if provided in response
    if (result.ip_usage) {
      ipUsage = result.ip_usage;
      updateUsageDisplay();
    }
    
    // Handle limit exceeded
    if (result.limit_exceeded) {
      const errorMsg = result.error || 'Usage limit exceeded. Please sign in for unlimited access.';
      showError(errorMsg);
      return { success: false, error: errorMsg };
    }
    
    return result;
  } catch (error) {
    // Handle 429 (Too Many Requests) specifically
    if (error.message.includes('429')) {
      showError('Usage limit exceeded. Please sign in for unlimited access.');
      ipUsage.limit_exceeded = true;
      updateUsageDisplay();
      return { success: false, error: 'Usage limit exceeded' };
    }
    throw error;
  }
};

// ========== END AUTHENTICATION FUNCTIONALITY ==========

// ========== MATCH EVENTS FUNCTIONALITY ==========

// Load match events for finished matches
async function loadMatchEvents(matchId, button) {
  try {
    console.log(`Loading events for match ${matchId}`);
    const eventsContainer = document.getElementById(`events-${matchId}`);
    
    // Show loading state
    eventsContainer.style.display = 'block';
    button.disabled = true;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
    
    // Fetch match events using plain fetch to avoid fetchJson wrapper issues
    const url = `/api/match-events/${matchId}`;
    console.log(`Fetching from: ${url}`);
    
    const fetchResponse = await fetch(url);
    console.log(`Response status: ${fetchResponse.status}`);
    
    if (!fetchResponse.ok) {
      if (fetchResponse.status === 429) {
        throw new Error('Usage limit exceeded. Please sign in for unlimited access.');
      }
      throw new Error(`HTTP ${fetchResponse.status}: ${fetchResponse.statusText}`);
    }
    
    const response = await fetchResponse.json();
    console.log('Response data:', response);
    
    if (response.success && response.data) {
      const events = response.data;
      console.log(`Rendering ${events.length} events`);
      eventsContainer.innerHTML = renderMatchEvents(events);
      
      // Update button to show/hide
      button.innerHTML = '<i class="fas fa-eye-slash"></i> Hide Events';
      button.setAttribute('data-action', 'hide');
      button.disabled = false;
    } else {
      console.log('No events or failed response:', response);
      eventsContainer.innerHTML = `<div class="no-events"><i class="fas fa-info-circle"></i> ${response.error || 'No events available for this match'}</div>`;
      button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> No Data';
      button.disabled = true;
    }
  } catch (error) {
    console.error('Error loading match events:', error);
    const eventsContainer = document.getElementById(`events-${matchId}`);
    
    if (error.message.includes('Usage limit exceeded')) {
      eventsContainer.innerHTML = `
        <div class="events-error usage-limit-error">
          <i class="fas fa-lock"></i> 
          <strong>Usage Limit Reached</strong>
          <p>You've reached the daily limit of 5 requests. Sign in for unlimited access!</p>
          <div class="limit-error-buttons">
            <button class="btn btn-primary auth-signin-btn">
              <i class="fas fa-sign-in-alt"></i> Sign In
            </button>
            <button class="btn btn-secondary auth-signup-btn">
              <i class="fas fa-user-plus"></i> Sign Up
            </button>
          </div>
        </div>`;
      button.innerHTML = '<i class="fas fa-lock"></i> Limit Reached';
    } else {
      eventsContainer.innerHTML = `<div class="events-error"><i class="fas fa-exclamation-triangle"></i> Failed to load events: ${error.message}</div>`;
      button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
    }
    button.disabled = true;
  }
}

// Hide match events
function hideMatchEvents(matchId, button) {
  console.log(`Hiding events for match ${matchId}`);
  const eventsContainer = document.getElementById(`events-${matchId}`);
  if (eventsContainer) {
    eventsContainer.style.display = 'none';
  }
  
  button.innerHTML = '<i class="fas fa-download"></i> Load Events';
  button.setAttribute('data-action', 'load');
  button.disabled = false;
}

// Render match events HTML
function renderMatchEvents(events) {
  if (!events || events.length === 0) {
    return '<div class="no-events"><i class="fas fa-info-circle"></i> No events recorded for this match</div>';
  }
  
  // Separate events by type
  const goals = events.filter(e => e.type === 'goal');
  const cards = events.filter(e => e.type === 'card');
  const substitutions = events.filter(e => e.type === 'substitution');
  
  let html = '<div class="events-content">';
  
  // Goals section
  if (goals.length > 0) {
    html += `
      <div class="event-type-section">
        <h6><i class="fas fa-futbol"></i> Goals (${goals.length})</h6>
        <div class="events-list goals-list">`;
    
    goals.forEach(goal => {
      const assistText = goal.assist_player ? ` (Assist: ${goal.assist_player})` : '';
      html += `
        <div class="event-item goal-event">
          <div class="event-time">${goal.minute}'</div>
          <div class="event-icon">⚽</div>
          <div class="event-details">
            <div class="event-player">${goal.player_name}</div>
            <div class="event-team">${goal.team_name}${assistText}</div>
          </div>
        </div>`;
    });
    
    html += '</div></div>';
  }
  
  // Cards section
  if (cards.length > 0) {
    html += `
      <div class="event-type-section">
        <h6><i class="fas fa-square"></i> Cards (${cards.length})</h6>
        <div class="events-list cards-list">`;
    
    cards.forEach(card => {
      const cardIcon = card.card_type === 'RED' ? '🟥' : '🟨';
      const cardClass = card.card_type === 'RED' ? 'red-card' : 'yellow-card';
      html += `
        <div class="event-item card-event ${cardClass}">
          <div class="event-time">${card.minute}'</div>
          <div class="event-icon">${cardIcon}</div>
          <div class="event-details">
            <div class="event-player">${card.player_name}</div>
            <div class="event-team">${card.team_name} - ${card.card_type} Card</div>
          </div>
        </div>`;
    });
    
    html += '</div></div>';
  }
  
  // Substitutions section (if available)
  if (substitutions.length > 0) {
    html += `
      <div class="event-type-section">
        <h6><i class="fas fa-exchange-alt"></i> Substitutions (${substitutions.length})</h6>
        <div class="events-list subs-list">`;
    
    substitutions.forEach(sub => {
      html += `
        <div class="event-item sub-event">
          <div class="event-time">${sub.minute}'</div>
          <div class="event-icon">🔄</div>
          <div class="event-details">
            <div class="event-player">${sub.player_name}</div>
            <div class="event-team">${sub.team_name} - Substitution</div>
          </div>
        </div>`;
    });
    
    html += '</div></div>';
  }
  
  html += '</div>';
  return html;
}

// Make function globally accessible (keeping for compatibility)
window.loadMatchEvents = loadMatchEvents;
window.hideMatchEvents = hideMatchEvents;

// ========== END MATCH EVENTS FUNCTIONALITY ==========

// ========== PRINT PREDICTIONS FUNCTIONALITY ==========

// Print predictions in table format
function printPredictionsTable() {
  if (!currentPredictions || currentPredictions.length === 0) {
    showError('No predictions available to print. Please load predictions first.');
    return;
  }
  
  // Generate table HTML
  const tableHtml = generatePredictionsTableHtml(currentPredictions);
  
  // Create a temporary print container
  let printContainer = document.getElementById('print-container');
  if (!printContainer) {
    printContainer = document.createElement('div');
    printContainer.id = 'print-container';
    printContainer.className = 'print-content';
    printContainer.style.display = 'none';
    document.body.appendChild(printContainer);
  }
  
  printContainer.innerHTML = tableHtml;
  printContainer.style.display = 'block';
  
  // Trigger print
  window.print();
  
  // Hide the print container after printing
  setTimeout(() => {
    printContainer.style.display = 'none';
  }, 1000);
}

// Generate HTML for predictions table
function generatePredictionsTableHtml(predictions) {
  const now = new Date();
  const dateStr = now.toLocaleDateString();
  const timeStr = now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
  
  // Check for active filters
  const outcomeFilter = $('outcome-filter')?.value || '';
  const dateFilter = $('prediction-date')?.value || '';
  
  let filterInfo = '';
  if (outcomeFilter || dateFilter) {
    filterInfo = '<div class="print-filters"><strong>Active Filters:</strong> ';
    if (outcomeFilter) {
      const outcomeLabels = {
        'WIN': 'Home/Away Wins Only',
        'DRAW': 'Draws Only',
        'ELITE_CONFIDENCE': 'Elite Confidence (80%+)',
        'HIGH_CONFIDENCE': 'High Confidence (70-79%)',
        'MEDIUM_CONFIDENCE': 'Medium Confidence (50-69%)',
        'LOW_CONFIDENCE': 'Low Confidence (Below 50%)'
      };
      filterInfo += `Outcome: ${outcomeLabels[outcomeFilter] || outcomeFilter}`;
    }
    if (dateFilter) {
      const filterDate = new Date(dateFilter + 'T00:00:00');
      const dayName = filterDate.toLocaleDateString('en-US', { weekday: 'short' });
      const formattedDate = filterDate.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        year: filterDate.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
      });
      if (outcomeFilter) filterInfo += ', ';
      filterInfo += `Date: ${dayName}, ${formattedDate}`;
    }
    filterInfo += '</div>';
  }
  
  let html = `
    <div class="print-header">
      <h1>Football Match Predictions</h1>
      <div class="print-date">Generated on: ${dateStr} at ${timeStr}</div>
      ${filterInfo}
      <div class="print-count">Total Predictions: ${predictions.length}</div>
    </div>
    
    <table class="print-table">
      <thead>
        <tr>
          <th>Date & Time</th>
          <th>Match</th>
          <th>Competition</th>
          <th>Prediction</th>
          <th>Confidence</th>
          <th>Probabilities</th>
          <th>Reasoning</th>
        </tr>
      </thead>
      <tbody>
  `;
  
  predictions.forEach(match => {
    if (!match.prediction) return;
    
    const matchDate = new Date(match.utcDate);
    const matchDateStr = matchDate.toLocaleDateString();
    const matchTimeStr = matchDate.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    const homeTeam = match.homeTeam?.name || 'TBD';
    const awayTeam = match.awayTeam?.name || 'TBD';
    const competition = match.competition?.name || 'Unknown';
    
    const prediction = match.prediction;
    const confidence = prediction.confidence || 0;
    const predictedTeam = prediction.predicted_team || 'Unknown';
    const reasoning = prediction.reasoning || 'No reasoning provided';
    
    // Determine confidence class for background color
    let confidenceClass = 'confidence-low';
    if (confidence >= 80) confidenceClass = 'confidence-high';
    else if (confidence >= 60) confidenceClass = 'confidence-medium';
    
    // Format probabilities
    let probabilities = 'N/A';
    if (prediction.probabilities) {
      const probs = prediction.probabilities;
      probabilities = `H: ${probs.home_win || 0}%, D: ${probs.draw || 0}%, A: ${probs.away_win || 0}%`;
    }
    
    html += `
      <tr class="${confidenceClass}">
        <td style="white-space: nowrap;">${matchDateStr}<br/>${matchTimeStr}</td>
        <td style="font-weight: bold;">${homeTeam}<br/>vs<br/>${awayTeam}</td>
        <td>${competition}</td>
        <td style="font-weight: bold; text-align: center;">${predictedTeam}</td>
        <td style="text-align: center; font-weight: bold;">${confidence}%</td>
        <td style="font-size: 11px;">${probabilities}</td>
        <td style="font-size: 11px;">${reasoning}</td>
      </tr>
    `;
  });
  
  html += `
      </tbody>
    </table>
    
    <div style="margin-top: 20px; font-size: 12px; color: #666; text-align: center;">
      <p>This report was generated by the Football Dashboard prediction system.</p>
      <p>Predictions are based on statistical analysis and should be used for informational purposes only.</p>
    </div>
  `;
  
  return html;
}

// ========== END PRINT PREDICTIONS FUNCTIONALITY ==========

// ========== DATE DROPDOWN FUNCTIONALITY ==========

// Populate date dropdown with available match dates
function populateDateDropdown(predictions) {
  const dateDropdown = $('prediction-date');
  if (!dateDropdown || !predictions || predictions.length === 0) return;
  
  // Extract unique dates from predictions
  const uniqueDates = new Set();
  predictions.forEach(match => {
    if (match.utcDate) {
      const matchDate = new Date(match.utcDate);
      const year = matchDate.getFullYear();
      const month = String(matchDate.getMonth() + 1).padStart(2, '0');
      const day = String(matchDate.getDate()).padStart(2, '0');
      const dateStr = `${year}-${month}-${day}`;
      uniqueDates.add(dateStr);
    }
  });
  
  // Convert to sorted array
  const sortedDates = Array.from(uniqueDates).sort();
  
  // Remember current selection
  const currentValue = dateDropdown.value;
  
  // Clear existing options except "All Dates"
  while (dateDropdown.options.length > 1) {
    dateDropdown.remove(1);
  }
  
  // Add date options
  sortedDates.forEach(dateStr => {
    const option = document.createElement('option');
    option.value = dateStr;
    
    // Format date for display
    const date = new Date(dateStr + 'T00:00:00');
    const dayName = date.toLocaleDateString('en-US', { weekday: 'short' });
    const formattedDate = date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: date.getFullYear() !== new Date().getFullYear() ? 'numeric' : undefined
    });
    
    option.textContent = `${dayName}, ${formattedDate}`;
    dateDropdown.appendChild(option);
  });
  
  // Restore selection if it still exists
  if (currentValue && Array.from(dateDropdown.options).some(opt => opt.value === currentValue)) {
    dateDropdown.value = currentValue;
  }
}

// ========== END DATE DROPDOWN FUNCTIONALITY ==========

// Enhanced prediction display functions
function getPredictionSourcesHtml(prediction) {
  if (!prediction) return '';
  
  // Check if this is an AI-Enhanced prediction
  const isAiEnhanced = prediction.prediction_method === 'AI-Enhanced Multi-Source';
  const sources = prediction.sources_used || [];
  const totalSources = prediction.total_sources || 0;
  
  if (!isAiEnhanced && totalSources === 0) {
    return `
      <div class="prediction-method-badge basic">
        <i class="fas fa-chart-line"></i>
        <span>Statistical Analysis</span>
      </div>`;
  }
  
  let sourcesHtml = '';
  if (isAiEnhanced && totalSources > 0) {
    sourcesHtml = `
      <div class="prediction-sources">
        <div class="sources-header">
          <i class="fas fa-globe-americas"></i>
          <span>AI-Enhanced Multi-Source Analysis</span>
          <div class="sources-count">${totalSources} sources</div>
        </div>
        <div class="sources-list">
          ${sources.slice(0, 3).map(source => `
            <div class="source-item ${source.type}">
              <div class="source-icon">
                ${getSourceIcon(source.type)}
              </div>
              <div class="source-info">
                <div class="source-name">${source.name}</div>
                <div class="source-confidence">${source.confidence}% confidence</div>
              </div>
            </div>
          `).join('')}
          ${sources.length > 3 ? `
            <div class="more-sources">+${sources.length - 3} more sources</div>
          ` : ''}
        </div>
        <div class="prediction-quality">
          <i class="fas fa-star"></i>
          <span>Quality: ${prediction.prediction_quality || 'standard'}</span>
        </div>
      </div>`;
  } else {
    sourcesHtml = `
      <div class="prediction-method-badge ${isAiEnhanced ? 'ai' : 'basic'}">
        <i class="fas ${isAiEnhanced ? 'fa-robot' : 'fa-chart-line'}"></i>
        <span>${prediction.prediction_method || 'Statistical Analysis'}</span>
      </div>`;
  }
  
  return sourcesHtml;
}

function getSourceIcon(sourceType) {
  switch (sourceType) {
    case 'web':
      return '<i class="fas fa-globe"></i>';
    case 'ai':
      return '<i class="fas fa-robot"></i>';
    case 'statistical':
      return '<i class="fas fa-chart-bar"></i>';
    case 'expert':
      return '<i class="fas fa-brain"></i>';
    default:
      return '<i class="fas fa-circle"></i>';
  }
}

// Function to show detailed prediction explanation
async function showPredictionExplanation(prediction) {
  try {
    const response = await fetchJson('/api/prediction-explanation', {}, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prediction })
    });
    
    if (response.success) {
      displayPredictionExplanation(response.explanation);
    } else {
      showError('Failed to get prediction explanation: ' + response.error);
    }
  } catch (error) {
    console.error('Error getting prediction explanation:', error);
    showError('Failed to load prediction explanation');
  }
}

function displayPredictionExplanation(explanation) {
  // Create and show modal with explanation
  let modal = document.getElementById('prediction-explanation-modal');
  if (!modal) {
    // Create modal if it doesn't exist
    modal = document.createElement('div');
    modal.id = 'prediction-explanation-modal';
    modal.className = 'modal';
    modal.innerHTML = `
      <div class="modal-content prediction-explanation">
        <div class="modal-header">
          <h3><i class="fas fa-info-circle"></i> Prediction Explanation</h3>
          <button class="modal-close" onclick="closePredictionExplanation()">&times;</button>
        </div>
        <div class="modal-body" id="explanation-content">
          <!-- Content will be populated here -->
        </div>
        <div class="modal-footer">
          <button class="btn btn-primary" onclick="closePredictionExplanation()">Close</button>
        </div>
      </div>`;
    document.body.appendChild(modal);
  }
  
  // Populate explanation content
  const content = document.getElementById('explanation-content');
  content.innerHTML = `
    <div class="explanation-section">
      <h4><i class="fas fa-cog"></i> Prediction Method</h4>
      <p><strong>${explanation.method}</strong> - ${explanation.confidence_level} confidence level</p>
    </div>
    
    ${explanation.sources_breakdown && explanation.sources_breakdown.length > 0 ? `
      <div class="explanation-section">
        <h4><i class="fas fa-database"></i> Sources Used</h4>
        <div class="sources-breakdown">
          ${explanation.sources_breakdown.map(source => `
            <div class="source-breakdown-item">
              <div class="source-header">
                ${getSourceIcon(source.type)}
                <strong>${source.name}</strong>
                <span class="source-confidence">${source.confidence}%</span>
              </div>
              <div class="source-prediction">Predicted: ${source.prediction}</div>
            </div>
          `).join('')}
        </div>
      </div>
    ` : ''}
    
    ${explanation.strengths && explanation.strengths.length > 0 ? `
      <div class="explanation-section">
        <h4><i class="fas fa-check-circle"></i> Strengths</h4>
        <ul>
          ${explanation.strengths.map(strength => `<li>${strength}</li>`).join('')}
        </ul>
      </div>
    ` : ''}
    
    ${explanation.risk_factors && explanation.risk_factors.length > 0 ? `
      <div class="explanation-section">
        <h4><i class="fas fa-exclamation-triangle"></i> Risk Factors</h4>
        <ul>
          ${explanation.risk_factors.map(risk => `<li>${risk}</li>`).join('')}
        </ul>
      </div>
    ` : ''}
    
    <div class="explanation-section">
      <h4><i class="fas fa-star"></i> Quality Assessment</h4>
      <p>This prediction is rated as <strong>${explanation.quality_assessment}</strong> quality.</p>
    </div>
  `;
  
  modal.style.display = 'block';
}

function closePredictionExplanation() {
  const modal = document.getElementById('prediction-explanation-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

// Function to get prediction sources info
async function loadPredictionSourcesInfo() {
  try {
    const response = await fetchJson('/api/prediction-sources');
    if (response.success) {
      updatePredictionMethodDisplay(response.sources);
    }
  } catch (error) {
    console.error('Error loading prediction sources:', error);
  }
}

function updatePredictionMethodDisplay(sources) {
  // Update the UI to show what prediction method is being used
  const predictionSection = document.querySelector('.section-header h2');
  if (predictionSection && predictionSection.textContent === 'Match Predictions') {
    const infoText = document.querySelector('.info-text');
    if (infoText) {
      let methodText = 'AI-powered match outcome predictions';
      if (sources.ai_enhanced_available) {
        methodText = `🤖 AI-Enhanced predictions from ${sources.web_sources || 5}+ web sources`;
      } else if (sources.gpt_available) {
        methodText = '🧠 GPT-powered intelligent predictions';
      } else {
        methodText = '📊 Statistical analysis predictions';
      }
      infoText.textContent = methodText;
    }
  }
}

// Make functions globally accessible
window.showPredictionExplanation = showPredictionExplanation;
window.closePredictionExplanation = closePredictionExplanation;

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  // Load user settings first
  loadUserSettings();
  
  // Check authentication status
  await checkAuthStatus();
  
  // Load prediction sources info
  loadPredictionSourcesInfo();
  
  // Fetch user location data for time conversion (don't wait)
  fetchUserLocationData();
  
  // Add event delegation for match events buttons
  document.addEventListener('click', function(e) {
    // Check if the clicked element or its parent is a match events button
    let button = null;
    if (e.target.classList.contains('load-events-btn')) {
      button = e.target;
    } else if (e.target.closest('.load-events-btn')) {
      button = e.target.closest('.load-events-btn');
    }
    
    if (button) {
      e.preventDefault();
      e.stopPropagation();
      
      const matchId = button.getAttribute('data-match-id');
      const action = button.getAttribute('data-action');
      
      console.log(`Match events button clicked - ID: ${matchId}, Action: ${action}`);
      
      if (action === 'load') {
        loadMatchEvents(matchId, button);
      } else if (action === 'hide') {
        hideMatchEvents(matchId, button);
      } else {
        console.warn('Unknown action:', action);
      }
    }
    
    // Handle auth buttons in error messages
    if (e.target.classList.contains('auth-signin-btn')) {
      e.preventDefault();
      showSignInModal();
    }
    
    if (e.target.classList.contains('auth-signup-btn')) {
      e.preventDefault();
      showSignUpModal();
    }
  });
  
  // Wire up tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });
  
  // Wire up authentication buttons
  const signinBtn = $('signin-btn');
  const signupBtn = $('signup-btn');
  const logoutBtn = $('logout-btn');
  
  if (signinBtn) {
    signinBtn.addEventListener('click', showSignInModal);
  }
  if (signupBtn) {
    signupBtn.addEventListener('click', showSignUpModal);
  }
  if (logoutBtn) {
    logoutBtn.addEventListener('click', confirmLogout);
  }
  
  // Wire up save predictions button
  const savePredictionsBtn = $('save-predictions-btn');
  if (savePredictionsBtn) {
    savePredictionsBtn.addEventListener('click', showSaveBatchModal);
  }
  
  // Wire up print predictions button
  const printPredictionsBtn = $('print-predictions-btn');
  if (printPredictionsBtn) {
    printPredictionsBtn.addEventListener('click', printPredictionsTable);
  }
  
  // Wire up batch selector
  const batchSelector = $('batch-selector');
  if (batchSelector) {
    batchSelector.addEventListener('change', () => {
      const loadBtn = $('load-batch-btn');
      const deleteBtn = $('delete-batch-btn');
      const hasSelection = batchSelector.value && batchSelector.value !== '';
      
      if (loadBtn) {
        loadBtn.disabled = !hasSelection;
      }
      if (deleteBtn) {
        deleteBtn.disabled = !hasSelection;
      }
    });
  }
  
  // Wire up load batch button
  const loadBatchBtn = $('load-batch-btn');
  if (loadBatchBtn) {
    loadBatchBtn.addEventListener('click', loadBatchComparison);
  }
  
  // Wire up delete batch button
  const deleteBatchBtn = $('delete-batch-btn');
  if (deleteBatchBtn) {
    deleteBatchBtn.addEventListener('click', showDeleteBatchModal);
  }
  
  // Initialize settings tab
  initializeSettingsTab();
  
  // Initialize time display
  initializeTimeDisplay();
  
  // Verify comparison modal exists
  const comparisonModal = $('comparison-details-modal');
  if (!comparisonModal) {
    console.warn('Comparison details modal not found in DOM');
  }

// =============================================
// CHATBOT FUNCTIONALITY
// =============================================

// Chatbot state
let chatbotState = {
  isOpen: false,
  isMinimized: false,
  messageHistory: []
};

function initializeChatbot() {
  const chatbotToggle = $('chatbot-toggle');
  const chatbotWindow = $('chatbot-window');
  const chatbotClose = $('chatbot-close');
  const chatbotMinimize = $('chatbot-minimize');
  const chatbotInput = $('chatbot-input');
  const chatbotSend = $('chatbot-send');
  
  if (!chatbotToggle || !chatbotWindow) {
    console.warn('Chatbot elements not found');
    return;
  }
  
  // Toggle chatbot window
  chatbotToggle.addEventListener('click', () => {
    if (chatbotState.isOpen) {
      closeChatbot();
    } else {
      openChatbot();
    }
  });
  
  // Close chatbot
  if (chatbotClose) {
    chatbotClose.addEventListener('click', closeChatbot);
  }
  
  // Minimize/restore chatbot
  if (chatbotMinimize) {
    chatbotMinimize.addEventListener('click', () => {
      if (chatbotState.isMinimized) {
        restoreChatbot();
      } else {
        minimizeChatbot();
      }
    });
  }
  
  // Input handling
  if (chatbotInput) {
    chatbotInput.addEventListener('input', () => {
      const sendBtn = $('chatbot-send');
      if (sendBtn) {
        sendBtn.disabled = !chatbotInput.value.trim();
      }
    });
    
    chatbotInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });
  }
  
  // Send button
  if (chatbotSend) {
    chatbotSend.addEventListener('click', sendChatMessage);
  }
}

function openChatbot() {
  const chatbotWindow = $('chatbot-window');
  if (chatbotWindow) {
    chatbotWindow.classList.add('active');
    chatbotWindow.classList.remove('minimized');
    chatbotState.isOpen = true;
    chatbotState.isMinimized = false;
    
    // Focus input
    const input = $('chatbot-input');
    if (input) {
      setTimeout(() => input.focus(), 300);
    }
  }
}

function closeChatbot() {
  const chatbotWindow = $('chatbot-window');
  if (chatbotWindow) {
    chatbotWindow.classList.remove('active');
    chatbotWindow.classList.remove('minimized');
    chatbotState.isOpen = false;
    chatbotState.isMinimized = false;
  }
}

function minimizeChatbot() {
  const chatbotWindow = $('chatbot-window');
  const minimizeBtn = $('chatbot-minimize');
  
  if (chatbotWindow && minimizeBtn) {
    chatbotWindow.classList.add('minimized');
    chatbotState.isMinimized = true;
    
    // Change minimize button to restore
    minimizeBtn.innerHTML = '<i class="fas fa-window-restore"></i>';
    minimizeBtn.title = 'Restore';
  }
}

function restoreChatbot() {
  const chatbotWindow = $('chatbot-window');
  const minimizeBtn = $('chatbot-minimize');
  
  if (chatbotWindow && minimizeBtn) {
    chatbotWindow.classList.remove('minimized');
    chatbotState.isMinimized = false;
    
    // Change restore button back to minimize
    minimizeBtn.innerHTML = '<i class="fas fa-minus"></i>';
    minimizeBtn.title = 'Minimize';
    
    // Focus input
    const input = $('chatbot-input');
    if (input) {
      setTimeout(() => input.focus(), 200);
    }
  }
}

function addChatMessage(message, isUser = false, timestamp = null) {
  const messagesContainer = $('chatbot-messages');
  if (!messagesContainer) return;
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
  
  const avatarDiv = document.createElement('div');
  avatarDiv.className = 'message-avatar';
  avatarDiv.innerHTML = `<i class="fas fa-${isUser ? 'user' : 'robot'}"></i>`;
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  
  const textDiv = document.createElement('div');
  textDiv.className = 'message-text';
  textDiv.textContent = message;
  
  const timeDiv = document.createElement('div');
  timeDiv.className = 'message-time';
  timeDiv.textContent = timestamp || formatTime(new Date());
  
  contentDiv.appendChild(textDiv);
  contentDiv.appendChild(timeDiv);
  
  messageDiv.appendChild(avatarDiv);
  messageDiv.appendChild(contentDiv);
  
  // Remove welcome message if it exists and this is the first real message
  const welcomeMessage = messagesContainer.querySelector('.welcome-message');
  if (welcomeMessage && chatbotState.messageHistory.length === 0) {
    welcomeMessage.remove();
  }
  
  messagesContainer.appendChild(messageDiv);
  
  // Scroll to bottom
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  // Add to history
  chatbotState.messageHistory.push({
    message,
    isUser,
    timestamp: timestamp || new Date().toISOString()
  });
}

function showTypingIndicator() {
  const typingIndicator = $('chatbot-typing');
  if (typingIndicator) {
    typingIndicator.style.display = 'flex';
  }
}

function hideTypingIndicator() {
  const typingIndicator = $('chatbot-typing');
  if (typingIndicator) {
    typingIndicator.style.display = 'none';
  }
}

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

async function sendChatMessage() {
  const input = $('chatbot-input');
  const sendBtn = $('chatbot-send');
  
  if (!input || !input.value.trim()) return;
  
  const message = input.value.trim();
  input.value = '';
  
  if (sendBtn) {
    sendBtn.disabled = true;
  }
  
  // Add user message to chat
  addChatMessage(message, true);
  
  // Show typing indicator
  showTypingIndicator();
  
  try {
    // Send message to API
    const response = await fetch('/api/chatbot', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message: message })
    });
    
    const data = await response.json();
    
    hideTypingIndicator();
    
    if (data.success) {
      // Add bot response to chat
      addChatMessage(data.response, false);
    } else {
      // Handle error
      let errorMessage = 'Sorry, I encountered an error. Please try again.';
      
      if (response.status === 429) {
        errorMessage = 'You\'ve reached your usage limit. Please sign in for unlimited access to the chatbot.';
      } else if (response.status === 503) {
        errorMessage = 'The chatbot service is currently unavailable. Please try again later.';
      } else if (data.error) {
        errorMessage = data.error;
      }
      
      addChatMessage(errorMessage, false);
      
      // Update usage info if provided
      if (data.ip_usage) {
        updateUsageInfo(data.ip_usage);
      }
    }
    
  } catch (error) {
    console.error('Chatbot error:', error);
    hideTypingIndicator();
    addChatMessage('Sorry, I\'m having trouble connecting. Please check your internet connection and try again.', false);
  } finally {
    if (sendBtn) {
      sendBtn.disabled = false;
    }
    input.focus();
  }
}

// =============================================
// END CHATBOT FUNCTIONALITY
// =============================================

  // Initialize chatbot
  initializeChatbot();
  
  // initial load
  await loadCompetitions();
  await loadPredictionBatches(); // Load available batches
  await loadAllData(true);
  startAutoRefresh();

  $('api-status').innerHTML = '<i class="fas fa-circle status-ok"></i> API Connected';
});
