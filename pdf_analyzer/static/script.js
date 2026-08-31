// ==========================================
// DOM ELEMENTS & GLOBAL STATE
// ==========================================
const uploadScreen = document.getElementById('upload-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const loadingOverlay = document.getElementById('loading-overlay');
const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');
const browseBtn = document.getElementById('browse-btn');

// Dashboard Elements
const articleTitle = document.getElementById('article-title');
const articleJournal = document.getElementById('article-journal');
const kpiPages = document.getElementById('kpi-pages');
const kpiAuthors = document.getElementById('kpi-authors');
const kpiHeadings = document.getElementById('kpi-headings');
const kpiReferences = document.getElementById('kpi-references');
const authorsList = document.getElementById('authors-list');
const headingsOutline = document.getElementById('headings-outline');
const referencesList = document.getElementById('references-list');
const xmlCode = document.getElementById('xml-code');

let currentXml = '';
let currentProjectId = '';
let currentProjectData = null;
let currentPaperRecord = null;
let currentProjectReferences = [];

// ==========================================
// THEME MANAGER (LIGHT / DARK)
// ==========================================
function initTheme() {
    const savedTheme = localStorage.getItem('app_theme') || 'light';
    applyTheme(savedTheme);
}

function applyTheme(theme) {
    if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
        const icon = document.getElementById('theme-icon');
        const text = document.getElementById('theme-text');
        if (icon) icon.textContent = '🌙';
        if (text) text.textContent = 'Dark';
    } else {
        document.documentElement.removeAttribute('data-theme');
        const icon = document.getElementById('theme-icon');
        const text = document.getElementById('theme-text');
        if (icon) icon.textContent = '☀️';
        if (text) text.textContent = 'Light';
    }
    localStorage.setItem('app_theme', theme);
}

function toggleTheme() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    applyTheme(isDark ? 'light' : 'dark');
    showToast(isDark ? 'Switched to Light Mode ☀️' : 'Switched to Dark Mode 🌙', 'info', 2000);
}

// Initialize theme immediately on load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTheme);
} else {
    initTheme();
}

// ==========================================
// TOAST NOTIFICATIONS SYSTEM
// ==========================================
function showToast(message, type = 'info', duration = 3200) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-message toast-${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✓';
    if (type === 'error') icon = '⚠️';
    if (type === 'warning') icon = '🔔';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-text">${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('toast-show');
    }, 10);

    setTimeout(() => {
        toast.classList.remove('toast-show');
        setTimeout(() => {
            if (toast.parentNode === container) {
                container.removeChild(toast);
            }
        }, 300);
    }, duration);
}

// ==========================================
// UPLOAD FLOW INITIALIZATION
// ==========================================
function initializeUploadFlow() {
    if (!dropZone || !fileInput) return;

    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--primary-color)';
        dropZone.style.boxShadow = '0 0 25px var(--primary-glow)';
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.style.borderColor = 'var(--panel-border)';
        dropZone.style.boxShadow = 'none';
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.style.borderColor = 'var(--panel-border)';
        dropZone.style.boxShadow = 'none';

        if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    dropZone.addEventListener('click', (e) => {
        if (e.target === dropZone || e.target.closest('#drop-zone')) {
            fileInput.click();
        }
    });

    if (browseBtn) {
        browseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            fileInput.click();
        });
    }

    fileInput.addEventListener('click', (e) => e.stopPropagation());
    fileInput.addEventListener('change', (e) => {
        if (fileInput.files && fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeUploadFlow);
} else {
    initializeUploadFlow();
}

// File processing and upload
function handleFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please upload a valid PDF document.', 'warning');
        fileInput.value = '';
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    showLoading(true);
    
    fetch('/analyze', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(errData => {
                throw new Error(errData.detail || 'Analysis failed.');
            }).catch(() => {
                throw new Error(`Server returned HTTP ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        currentProjectData = data;
        currentProjectId = data.project_id || '';
        populateDashboard(data);
        showScreen(dashboardScreen);
        showLoading(false);
        showToast('PDF parsed successfully! Enriching references from academic providers...', 'success');
        
        if (data.references && data.references.length > 0) {
            enrichDashboardReferences(data.references, currentProjectId);
        }
    })
    .catch(error => {
        console.error("PDF Upload Error:", error);
        showToast(`An error occurred while analyzing the PDF: ${error.message}`, 'error', 5000);
        showLoading(false);
    })
    .finally(() => {
        fileInput.value = '';
    });
}

// Background Reference & Master Record Enrichment
function enrichDashboardReferences(references, projectId = '') {
    const items = references.map(r => ({ text: r.text || r.original_text || '' }));
    
    fetch('/references/enrich', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ references: items, project_id: projectId })
    })
    .then(res => res.json())
    .then(data => {
        if (data && data.results && data.results.length > 0) {
            currentProjectReferences = data.results;
            renderReferencesList(data.results);
            showToast(`Enriched ${data.results.length} references with multi-source intelligence!`, 'success');
        }
    })
    .catch(err => {
        console.warn("Background reference enrichment skipped:", err);
    });
}

// UI Helpers
function showLoading(show) {
    if (loadingOverlay) {
        loadingOverlay.style.display = show ? 'flex' : 'none';
    }
}

function showScreen(screen) {
    if (!screen) return;
    uploadScreen.style.display = 'none';
    dashboardScreen.style.display = 'none';
    uploadScreen.classList.remove('active');
    dashboardScreen.classList.remove('active');
    
    screen.style.display = 'block';
    void screen.offsetWidth;
    screen.classList.add('active');
}

function showUploadScreen() {
    showScreen(uploadScreen);
    fileInput.value = '';
}

// Populate Dashboard Content
function populateDashboard(data) {
    if (!data) return;

    articleTitle.textContent = data.title || 'Untitled Article';
    
    let subHeader = data.journal || 'Academic Article';
    if (data.doi) subHeader += ` • DOI: ${data.doi}`;
    if (data.arxiv_id) subHeader += ` • arXiv: ${data.arxiv_id}`;
    articleJournal.textContent = subHeader;
    
    kpiPages.textContent = data.page_count !== undefined ? data.page_count : '-';
    kpiAuthors.textContent = Array.isArray(data.authors) ? data.authors.length : 0;
    kpiHeadings.textContent = Array.isArray(data.headings) ? data.headings.length : 0;
    
    const refsList = (Array.isArray(data.enriched_references) && data.enriched_references.length > 0)
        ? data.enriched_references
        : (Array.isArray(data.references) ? data.references : []);
    currentProjectReferences = refsList;
    kpiReferences.textContent = refsList.length;
    
    currentXml = data.xml || '';
    xmlCode.textContent = data.xml || '';
    
    // Abstract
    const abstractSec = document.getElementById('abstract-section');
    const abstractTxt = document.getElementById('abstract-text');
    if (data.abstract) {
        abstractSec.style.display = 'block';
        abstractTxt.textContent = data.abstract;
    } else {
        abstractSec.style.display = 'none';
    }
    
    // Standalone Keywords Card
    const kwSec = document.getElementById('keywords-section');
    const kwContainer = document.getElementById('keywords-container');
    if (data.keywords && data.keywords.length > 0) {
        kwSec.style.display = 'block';
        kwContainer.innerHTML = '';
        data.keywords.forEach(kw => {
            const tag = document.createElement('span');
            tag.className = 'keyword-pill';
            tag.innerHTML = `🏷️ ${escapeHtml(kw)}`;
            kwContainer.appendChild(tag);
        });
    } else {
        kwSec.style.display = 'none';
    }
    
    // Reset Analysis Tab
    document.getElementById('analysis-placeholder').style.display = 'flex';
    document.getElementById('analysis-details').style.display = 'none';
    switchRightTab('xml');
    
    // Populate Authors List
    authorsList.innerHTML = '';
    if (Array.isArray(data.authors)) {
        data.authors.forEach(author => {
            const nameStr = typeof author === 'object' ? (author.name || author.display_name || 'Author') : String(author || 'Author');
            const authorId = typeof author === 'object' ? (author.author_id || author.id || '') : '';
            const initials = nameStr.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'A';
            
            const chip = document.createElement('div');
            chip.className = 'author-chip';
            chip.style.cursor = 'pointer';
            chip.title = `Click to view Academic Profile for ${nameStr}`;
            chip.innerHTML = `
                <div class="author-avatar">${initials}</div>
                <div class="author-name">${escapeHtml(nameStr)}</div>
            `;
            chip.onclick = (e) => {
                e.stopPropagation();
                openAuthorProfile(authorId || nameStr, nameStr);
            };
            authorsList.appendChild(chip);
        });
    }
    
    // Affiliations
    const affilContainer = document.getElementById('affiliations-list');
    if (data.affiliations && data.affiliations.length > 0) {
        affilContainer.innerHTML = '<strong>Affiliations:</strong><br>' + data.affiliations.map(a => escapeHtml(a)).join('<br>');
    } else {
        affilContainer.innerHTML = '';
    }
    
    // Populate Headings Outline
    headingsOutline.innerHTML = '';
    if (!Array.isArray(data.headings) || data.headings.length === 0) {
        headingsOutline.innerHTML = '<div class="text-muted" style="padding: 1rem;">No headings identified in the document structure.</div>';
    } else {
        data.headings.forEach(heading => {
            const item = document.createElement('div');
            item.className = `heading-item level-${heading.level || 1}`;
            item.innerHTML = `
                ${escapeHtml(heading.text || '')}
                <span class="heading-page">P. ${heading.page || 1}</span>
            `;
            item.onclick = () => analyzeElement('heading', { text: heading.text || '', level: heading.level || 1, page: heading.page || 1 });
            headingsOutline.appendChild(item);
        });
    }

    // Populate References List
    renderReferencesList(refsList);
}

// ==========================================
// REDESIGNED ACADEMIC REFERENCE RESULT CARD
// ==========================================
function renderReferencesList(refsList) {
    if (!referencesList) return;
    referencesList.innerHTML = '';
    
    if (!Array.isArray(refsList) || refsList.length === 0) {
        referencesList.innerHTML = '<div class="text-muted" style="padding: 1.5rem; text-align: center;">No references identified in the bibliography section.</div>';
        return;
    }
    
    refsList.forEach((ref, idx) => {
        const item = document.createElement('div');
        item.className = 'ref-academic-card glass-panel';
        
        const refId = ref.reference_id || ref.id || `ref_${idx + 1}`;
        const refText = ref.original_text || ref.text || '';
        const cleanQuery = cleanRefQuery(refText);
        const encodedQuery = encodeURIComponent(cleanQuery);
        
        const master = ref.master_record || {};
        const canonical = master.canonical || {};
        const inputParsed = (master.input && master.input.parsed) || {};
        const sources = master.sources || {};
        const scholarSource = sources.google_scholar || {};
        const scholarData = scholarSource.data || {};

        // Extract metadata
        const displayTitle = (canonical.title && canonical.title.value) || ref.title || cleanQuery || 'Untitled Reference';
        const displayYear = (canonical.year && canonical.year.value) || ref.year || inputParsed.year || null;
        const displayVenue = (canonical.venue && canonical.venue.value) || ref.journal || inputParsed.journal || null;
        const displayType = (canonical.reference_type && canonical.reference_type.value) || inputParsed.reference_type || 'journal-article';
        const displayPublisher = (canonical.publisher && canonical.publisher.value) || inputParsed.publisher || null;
        const displayVolume = canonical.volume || inputParsed.volume || null;
        const displayIssue = canonical.issue || inputParsed.issue || null;
        const displayPages = canonical.pages || inputParsed.pages || null;
        
        // Identifiers
        const doiVal = (canonical.identifiers && canonical.identifiers.doi && canonical.identifiers.doi.value) || ref.doi || inputParsed.doi || null;
        const arxivVal = (canonical.identifiers && canonical.identifiers.arxiv_id && canonical.identifiers.arxiv_id.value) || ref.arxiv_id || inputParsed.arxiv_id || null;
        const isbnVal = (canonical.identifiers && canonical.identifiers.isbn && canonical.identifiers.isbn.value) || inputParsed.isbn || null;
        const openalexId = (canonical.identifiers && canonical.identifiers.openalex_id && canonical.identifiers.openalex_id.value) || null;
        const clusterId = (canonical.identifiers && canonical.identifiers.google_scholar_cluster_id && canonical.identifiers.google_scholar_cluster_id.value) || (scholarData && scholarData.cluster_id) || '';
        const scholarResultUrl = (canonical.identifiers && canonical.identifiers.google_scholar_url && canonical.identifiers.google_scholar_url.value) || ref.scholar_url || (scholarData && scholarData.link) || `https://scholar.google.com/scholar?q=${encodedQuery}`;

        // PDF Link
        let directPdfUrl = '';
        if (scholarData && Array.isArray(scholarData.resources)) {
            const pdfRes = scholarData.resources.find(r => (r.file_format || '').toLowerCase() === 'pdf' || (r.link || '').endsWith('.pdf'));
            if (pdfRes && pdfRes.link) directPdfUrl = pdfRes.link;
        }

        // Reference Type Label & Class
        let typeBadgeClass = 'badge-type-article';
        let typeLabel = 'JOURNAL ARTICLE';
        if (displayType === 'proceedings-article') {
            typeBadgeClass = 'badge-type-conference';
            typeLabel = 'CONFERENCE PAPER';
        } else if (displayType === 'book') {
            typeBadgeClass = 'badge-type-book';
            typeLabel = 'BOOK';
        } else if (displayType === 'book-chapter') {
            typeBadgeClass = 'badge-type-chapter';
            typeLabel = 'BOOK CHAPTER';
        } else if (displayType === 'preprint') {
            typeBadgeClass = 'badge-type-preprint';
            typeLabel = 'PREPRINT';
        }

        // Match status badge
        let matchBadge = '';
        if (ref.match_status === 'matched') {
            matchBadge = `<span class="badge-matched">✓ VERIFIED</span>`;
        } else if (ref.match_status === 'low_confidence') {
            matchBadge = `<span class="badge-low">⚠️ LOW CONFIDENCE</span>`;
        }

        // Citation counts (Null safe: Never show 0 if null, show "—")
        const citeCounts = canonical.citation_counts || ref.citations || {};
        const canonicalCiteVal = citeCounts.canonical_value !== undefined && citeCounts.canonical_value !== null ? citeCounts.canonical_value : (ref.citation_count !== undefined ? ref.citation_count : null);
        const alexCite = (citeCounts.openalex !== undefined && citeCounts.openalex !== null) 
            ? citeCounts.openalex 
            : ((sources.openalex && sources.openalex.citation_count !== undefined && sources.openalex.citation_count !== null) ? sources.openalex.citation_count : (ref.source === 'openalex' ? ref.citation_count : null));
        const crossCite = (citeCounts.crossref !== undefined && citeCounts.crossref !== null)
            ? citeCounts.crossref
            : ((sources.crossref && sources.crossref.citation_count !== undefined && sources.crossref.citation_count !== null) ? sources.crossref.citation_count : (ref.source === 'crossref' ? ref.citation_count : null));
        const scholarCite = (citeCounts.google_scholar !== undefined && citeCounts.google_scholar !== null)
            ? citeCounts.google_scholar
            : ((sources.google_scholar && sources.google_scholar.citation_count !== undefined && sources.google_scholar.citation_count !== null) ? sources.google_scholar.citation_count : (ref.source === 'google_scholar' ? ref.citation_count : null));

        // Provider Status Badges
        const alexStatus = (sources.openalex && sources.openalex.status) || (ref.source === 'openalex' ? ref.match_status : null);
        const crossStatus = (sources.crossref && sources.crossref.status) || (ref.source === 'crossref' ? ref.match_status : null);
        const scholarStatus = (sources.google_scholar && sources.google_scholar.status) || (ref.source === 'google_scholar' ? ref.match_status : null);

        let providerBadges = [];
        if (alexStatus === 'matched') {
            providerBadges.push(`<span class="badge-provider badge-prov-matched" title="Verified in OpenAlex">🌐 OpenAlex: ✓</span>`);
        } else if (alexStatus === 'low_confidence') {
            providerBadges.push(`<span class="badge-provider badge-prov-low" title="OpenAlex Low Confidence">🌐 OpenAlex: ⚠️</span>`);
        } else if (alexStatus === 'not_found') {
            providerBadges.push(`<span class="badge-provider badge-prov-missing" title="OpenAlex: Not Found">🌐 OpenAlex: ✕</span>`);
        }

        if (crossStatus === 'matched') {
            providerBadges.push(`<span class="badge-provider badge-prov-matched" title="Verified in Crossref">🔗 Crossref: ✓</span>`);
        } else if (crossStatus === 'low_confidence') {
            providerBadges.push(`<span class="badge-provider badge-prov-low" title="Crossref Low Confidence">🔗 Crossref: ⚠️</span>`);
        }

        if (scholarStatus === 'matched') {
            providerBadges.push(`<span class="badge-provider badge-prov-matched" title="Found in Google Scholar">🎓 Scholar: ✓</span>`);
        }

        const providersHtml = providerBadges.length > 0 ? `<div class="ref-providers-row">${providerBadges.join(' ')}</div>` : '';

        // Authors List Handling (Show all real authors, with +X more authors expandable chip if > 4)
        const allAuthors = (master.canonical_authors && master.canonical_authors.length > 0)
            ? master.canonical_authors
            : (Array.isArray(ref.authors) ? ref.authors : (inputParsed.authors || []));

        let authorsHtml = '';
        const firstAuthorName = allAuthors.length > 0 ? (typeof allAuthors[0] === 'object' ? allAuthors[0].name : String(allAuthors[0])) : '';

        if (allAuthors.length > 0) {
            authorsHtml = '<div class="ref-authors-container">';
            const authorsToShow = allAuthors.length > 5 ? allAuthors.slice(0, 4) : allAuthors;
            
            authorsToShow.forEach(a => {
                const aName = typeof a === 'object' ? (a.name || a.display_name || '') : String(a);
                const aId = typeof a === 'object' ? (a.author_id || (a.identifiers && (a.identifiers.openalex_id || a.identifiers.google_scholar_id)) || '') : '';
                const aOrcid = typeof a === 'object' ? (a.identifiers && a.identifiers.orcid) : null;
                const aScholarId = typeof a === 'object' ? (a.identifiers && a.identifiers.google_scholar_id) : null;
                const aOpenAlexId = typeof a === 'object' ? (a.identifiers && a.identifiers.openalex_id) : null;
                const initials = aName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'A';

                let idBadges = '';
                if (aOrcid) idBadges += `<span class="author-orcid-badge" title="ORCID: ${escapeHtml(aOrcid)}">🆔</span>`;
                if (aScholarId) idBadges += `<span class="author-scholar-badge" title="Scholar ID: ${escapeHtml(aScholarId)}">🎓</span>`;
                if (aOpenAlexId) idBadges += `<span class="author-openalex-badge" title="OpenAlex ID: ${escapeHtml(aOpenAlexId)}">🌐</span>`;

                authorsHtml += `
                    <div class="author-chip author-card-chip" onclick="event.stopPropagation(); openAuthorProfile('${escapeHtml(aId)}', '${escapeHtml(aName)}')">
                        <span class="author-avatar">${initials}</span>
                        <span class="author-name">${escapeHtml(aName)}</span>
                        ${idBadges}
                    </div>
                `;
            });

            if (allAuthors.length > 5) {
                const remaining = allAuthors.length - 4;
                authorsHtml += `
                    <div class="author-chip author-card-chip author-chip-more" onclick="event.stopPropagation(); openPaperModalToTab('${escapeHtml(refId)}', 'authors', ${escapeHtml(JSON.stringify(ref))})">
                        <span class="author-name">+${remaining} more authors</span>
                    </div>
                `;
            }
            authorsHtml += '</div>';
        }

        // Bibliographic Details Box (Adapts to Books / Chapters / Articles)
        let biblioParts = [];
        if (displayType === 'book') {
            if (displayPublisher) biblioParts.push(`<strong>🏢 Publisher:</strong> ${escapeHtml(displayPublisher)}`);
            if (displayYear) biblioParts.push(`<strong>📅 Year:</strong> ${displayYear}`);
            if (isbnVal) biblioParts.push(`<strong>📚 ISBN:</strong> ${escapeHtml(isbnVal)}`);
        } else if (displayType === 'book-chapter') {
            if (displayVenue) biblioParts.push(`<strong>📚 Book:</strong> ${escapeHtml(displayVenue)}`);
            if (displayPublisher) biblioParts.push(`<strong>🏢 Publisher:</strong> ${escapeHtml(displayPublisher)}`);
            if (displayYear) biblioParts.push(`<strong>📅 Year:</strong> ${displayYear}`);
            if (displayPages) biblioParts.push(`<strong>📄 pp:</strong> ${escapeHtml(displayPages)}`);
        } else {
            if (displayVenue) biblioParts.push(`<strong>📖 Venue:</strong> ${escapeHtml(displayVenue)}`);
            if (displayPublisher) biblioParts.push(`<strong>🏢 Publisher:</strong> ${escapeHtml(displayPublisher)}`);
            if (displayYear) biblioParts.push(`<strong>📅 Year:</strong> ${displayYear}`);
            
            let vipParts = [];
            if (displayVolume) vipParts.push(`Vol. ${displayVolume}`);
            if (displayIssue) vipParts.push(`No. ${displayIssue}`);
            if (displayPages) vipParts.push(`pp. ${displayPages}`);
            if (vipParts.length > 0) biblioParts.push(`<strong>📄 Pagination:</strong> ${vipParts.join(', ')}`);
        }

        const biblioHtml = biblioParts.length > 0 ? `<div class="ref-biblio-summary">${biblioParts.join(' &nbsp;•&nbsp; ')}</div>` : '';

        // Identifiers Row
        let idBadges = [];
        if (doiVal) {
            idBadges.push(`<a href="https://doi.org/${escapeHtml(doiVal)}" target="_blank" class="badge-id badge-id-doi" onclick="event.stopPropagation();">🔗 DOI: ${escapeHtml(doiVal)}</a>`);
        }
        if (arxivVal) {
            idBadges.push(`<a href="https://arxiv.org/abs/${escapeHtml(arxivVal)}" target="_blank" class="badge-id badge-id-arxiv" onclick="event.stopPropagation();">🔬 arXiv: ${escapeHtml(arxivVal)}</a>`);
        }
        if (isbnVal) {
            idBadges.push(`<span class="badge-id badge-id-isbn">📚 ISBN: ${escapeHtml(isbnVal)}</span>`);
        }
        if (openalexId) {
            idBadges.push(`<a href="${escapeHtml(openalexId)}" target="_blank" class="badge-id badge-id-openalex" onclick="event.stopPropagation();">🌐 OpenAlex</a>`);
        }
        if (clusterId) {
            idBadges.push(`<span class="badge-id badge-id-cluster" title="Scholar Cluster ID">🎓 Cluster: ${escapeHtml(clusterId)}</span>`);
        }

        const idsHtml = idBadges.length > 0 ? `<div class="ref-identifiers-row">${idBadges.join(' ')}</div>` : '';

        // Citation Intelligence Box in Reference Card
        const citeBoxHtml = `
            <div class="card-citation-intel-box">
                <div class="intel-header-label">📊 Citation Intelligence</div>
                <div class="intel-metrics-row">
                    <div class="intel-metric-item">
                        <span class="im-source">🎓 Google Scholar</span>
                        <span class="im-val">${scholarCite !== null && scholarCite !== undefined ? scholarCite.toLocaleString() : '—'}</span>
                    </div>
                    <div class="intel-metric-item">
                        <span class="im-source">🌐 OpenAlex</span>
                        <span class="im-val">${alexCite !== null && alexCite !== undefined ? alexCite.toLocaleString() : '—'}</span>
                    </div>
                    <div class="intel-metric-item">
                        <span class="im-source">🔗 Crossref</span>
                        <span class="im-val">${crossCite !== null && crossCite !== undefined ? crossCite.toLocaleString() : '—'}</span>
                    </div>
                </div>
            </div>
        `;

        // Find Citations Button text with count
        let findCitesLabel = '📊 Find Citations';
        const bestCiteCount = scholarCite || canonicalCiteVal;
        if (bestCiteCount !== null && bestCiteCount !== undefined) {
            findCitesLabel = `📊 Find Citations · ${bestCiteCount.toLocaleString()}`;
        }

        // Action Toolbar
        item.innerHTML = `
            <div class="ref-card-header">
                <div style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                    <span class="ref-index-badge">#${idx + 1}</span>
                    <span class="badge-ref-type ${typeBadgeClass}">${typeLabel}</span>
                    ${matchBadge}
                </div>
                ${providersHtml}
            </div>

            <div class="ref-card-title-row" onclick="openPaperModal('${escapeHtml(refId)}', ${escapeHtml(JSON.stringify(ref))})">
                <h4 class="ref-card-title">${escapeHtml(displayTitle)}</h4>
            </div>

            ${authorsHtml}
            ${biblioHtml}
            ${idsHtml}
            ${citeBoxHtml}

            <div class="ref-card-actions">
                <button class="btn-action-primary" onclick="event.stopPropagation(); openPaperModalToTab('${escapeHtml(refId)}', 'citations', ${escapeHtml(JSON.stringify(ref))})">${findCitesLabel}</button>
                <button class="btn-action-secondary" onclick="event.stopPropagation(); openPaperModal('${escapeHtml(refId)}', ${escapeHtml(JSON.stringify(ref))})">📖 Open Paper Profile</button>
                <button class="btn-action-secondary" onclick="event.stopPropagation(); openPaperModalToTab('${escapeHtml(refId)}', 'authors', ${escapeHtml(JSON.stringify(ref))})">👥 Authors</button>
                <button class="btn-action-secondary" onclick="event.stopPropagation(); openPaperModalToTab('${escapeHtml(refId)}', 'overview', ${escapeHtml(JSON.stringify(ref))})">🔍 View Sources</button>
                <a href="${scholarResultUrl}" target="_blank" class="btn-scholar-ref" onclick="event.stopPropagation();">🎓 Open Scholar</a>
                ${directPdfUrl ? `<a href="${directPdfUrl}" target="_blank" class="btn-pdf-link" onclick="event.stopPropagation();">📄 PDF</a>` : ''}
                <button class="btn-scholar-ref" onclick="event.stopPropagation(); searchPaperOptimized('${escapeHtml(displayTitle)}', '${escapeHtml(firstAuthorName)}', '${displayYear || ''}')">🔎 Search Paper</button>
                ${doiVal ? `<button class="btn-action-secondary" onclick="event.stopPropagation(); copyText('${escapeHtml(doiVal)}', 'DOI copied!')">📋 Copy DOI</button>` : ''}
                <button class="btn-action-secondary" onclick="event.stopPropagation(); copySingleRefBibtex(${escapeHtml(JSON.stringify(ref))}, ${idx + 1})">📋 BibTeX</button>
            </div>
        `;
        
        referencesList.appendChild(item);
    });
}

// Clean reference text to isolate title
function cleanRefQuery(refText) {
    if (!refText) return '';
    let text = refText.trim();
    text = text.replace(/^(?:\[\d+\]|\(\d+\)|\d+\.)\s*/, '');
    text = text.replace(/(\w+)-\s+(\w+)/g, '$1$2');
    
    const quoteMatch = text.match(/["“']([^"”']{8,})["”']/);
    if (quoteMatch && quoteMatch[1].length > 8) {
        return quoteMatch[1].trim();
    }
    
    const yearMatch = text.match(/\(\d{4}[a-z]?\)[\.,\s]*/);
    if (yearMatch && yearMatch.index !== undefined) {
        const titlePart = text.substring(yearMatch.index + yearMatch[0].length).trim();
        if (titlePart.length > 5) {
            const parts = titlePart.split(/\.(?!\s*[A-Z]\b)\s+/);
            if (parts[0] && parts[0].length > 8) {
                return parts[0].trim();
            }
            return titlePart;
        }
    }
    
    const sentences = text.split(/\.(?!\s*[A-Z]\b)\s+/);
    if (sentences.length >= 2) {
        if (sentences[0].length > 15 && !sentences[0].match(/^(?:[A-Z][a-z]+,?\s+)+/)) {
            return sentences[0].trim();
        } else if (sentences[1] && sentences[1].length > 8) {
            return sentences[1].trim();
        }
    }
    
    return text.trim() || refText.trim();
}

// Tab Switching (Right Panel)
function switchRightTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    
    if (tabName === 'xml') {
        document.getElementById('tab-xml-btn').classList.add('active');
        document.getElementById('tab-xml-content').classList.add('active');
    } else if (tabName === 'analysis') {
        document.getElementById('tab-analysis-btn').classList.add('active');
        document.getElementById('tab-analysis-content').classList.add('active');
    }
}

// Show Element Analysis Details
function analyzeElement(type, data) {
    switchRightTab('analysis');
    
    document.getElementById('analysis-placeholder').style.display = 'none';
    const detailsDiv = document.getElementById('analysis-details');
    detailsDiv.style.display = 'block';
    
    const typeTitle = document.getElementById('analysis-type-title');
    const textVal = document.getElementById('analysis-text');
    const typeVal = document.getElementById('analysis-type');
    const charsVal = document.getElementById('analysis-chars');
    const wordsVal = document.getElementById('analysis-words');
    const pageRow = document.getElementById('analysis-page-row');
    const pageVal = document.getElementById('analysis-page');
    const notesVal = document.getElementById('analysis-notes');
    
    textVal.textContent = data.text;
    charsVal.textContent = data.text.length;
    wordsVal.textContent = data.text.split(/\s+/).filter(Boolean).length;
    
    if (type === 'author') {
        typeTitle.textContent = '👤 Author Analysis';
        typeVal.textContent = 'Document Author / Contributor';
        pageRow.style.display = 'none';
        
        const words = data.text.split(' ');
        let notes = `This name contains ${words.length} parts. `;
        if (words.length === 2) {
            notes += "Matches standard First-Name Last-Name format.";
        } else if (words.length > 2) {
            notes += "Includes middle names or patronymic/nobiliary particles.";
        }
        notes += `<div style="margin-top: 1rem;"><button class="btn-action-primary" onclick="openAuthorProfile('${escapeHtml(data.text)}', '${escapeHtml(data.text)}')">🌐 Open Academic Profile (OpenAlex / Scholar)</button></div>`;
        notesVal.innerHTML = notes;
    } else if (type === 'heading') {
        typeTitle.textContent = '📂 Heading Analysis';
        typeVal.textContent = `Document Section Heading (Level ${data.level})`;
        pageRow.style.display = 'flex';
        pageVal.textContent = data.page;
        
        let notes = `This heading is placed on page ${data.page}. `;
        if (data.level === 1) {
            notes += "Classified as a major structural section (H1). It marks a primary division in the manuscript's outline.";
        } else {
            notes += `Classified as a subsection (H${data.level}). It organizes details under a parent heading.`;
        }
        notesVal.innerHTML = notes;
    }
}

// Clipboard copy helper
function copyXml() {
    navigator.clipboard.writeText(currentXml)
        .then(() => showToast('XML content copied to clipboard!', 'success'))
        .catch(err => console.error('Could not copy text: ', err));
}

// Download XML helper
function downloadXml() {
    const blob = new Blob([currentXml], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${articleTitle.textContent.replace(/[^a-z0-9]/gi, '_').toLowerCase()}_structure.xml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('XML file downloaded.', 'info');
}

function copyText(text, successMsg = 'Copied to clipboard!') {
    navigator.clipboard.writeText(text)
        .then(() => showToast(successMsg, 'success'))
        .catch(err => console.error('Clipboard copy error:', err));
}

// HTML escape helper
function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ==========================================
// GOOGLE SCHOLAR IN-SITE SEARCH LOGIC
// ==========================================
function executeScholarSearch() {
    const input = document.getElementById('scholar-search-input');
    const query = (input ? input.value : '').trim();
    if (!query) {
        showToast('Please enter a paper title, keyword, or author name to search Google Scholar.', 'warning');
        return;
    }
    searchPaperOnScholar(query);
}

function searchPaperOptimized(title, firstAuthor = '', year = '') {
    let q = title.trim();
    if (firstAuthor) q += ` ${firstAuthor.trim()}`;
    if (year) q += ` ${year.trim()}`;
    searchPaperOnScholar(q);
}

function searchPaperOnScholar(query) {
    if (!query) return;
    const input = document.getElementById('scholar-search-input');
    if (input) input.value = query;

    const sec = document.getElementById('scholar-results-section');
    const titleEl = document.getElementById('scholar-results-title');
    const loadingEl = document.getElementById('scholar-results-loading');
    const listEl = document.getElementById('scholar-results-list');

    sec.style.display = 'block';
    titleEl.textContent = `Google Scholar Results for "${query}"`;
    loadingEl.style.display = 'block';
    listEl.innerHTML = '';
    
    sec.scrollIntoView({ behavior: 'smooth', block: 'start' });

    fetch(`/scholar/search?q=${encodeURIComponent(query)}&num=10`)
        .then(res => res.json())
        .then(data => {
            loadingEl.style.display = 'none';
            renderScholarSearchResults(data);
        })
        .catch(err => {
            console.error('Scholar Search Error:', err);
            loadingEl.style.display = 'none';
            listEl.innerHTML = `<div class="scholar-fallback-banner">⚠️ Google Scholar search failed. Please try again.</div>`;
        });
}

function closeScholarSearchResults() {
    const sec = document.getElementById('scholar-results-section');
    if (sec) sec.style.display = 'none';
}

function renderScholarSearchResults(data) {
    const listEl = document.getElementById('scholar-results-list');
    listEl.innerHTML = '';

    if (!data.available) {
        const reasonMsg = data.reason === 'SERPAPI_KEY_NOT_CONFIGURED'
            ? 'Google Scholar integration is not configured.'
            : (data.error && data.error.detail ? data.error.detail : 'Google Scholar temporarily unavailable.');
        
        listEl.innerHTML = `
            <div class="scholar-fallback-banner">
                <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem;">🎓 Google Scholar data unavailable</div>
                <div style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.85rem;">
                    ${escapeHtml(reasonMsg)}<br>You can still search this paper directly on Google Scholar:
                </div>
                <a href="${escapeHtml(data.scholar_url)}" target="_blank" class="btn-scholar-ref" style="display: inline-block;">🎓 Search on Google Scholar</a>
            </div>
        `;
        return;
    }

    const results = data.results || [];
    if (results.length === 0) {
        listEl.innerHTML = `<div class="text-muted" style="padding: 1.5rem; text-align: center;">No citing papers were returned for this query.</div>`;
        return;
    }

    results.forEach((item, idx) => {
        const card = document.createElement('div');
        card.className = 'scholar-card glass-panel';

        // Authors list
        const authorsArr = (item.authors || []).map(a => {
            if (a.author_id) {
                return `<span class="author-link-chip" onclick="openAuthorProfile('${escapeHtml(a.author_id)}', '${escapeHtml(a.name)}')">👤 ${escapeHtml(a.name)}</span>`;
            }
            return `<span class="text-muted">${escapeHtml(a.name)}</span>`;
        }).join(', ') || 'Unknown Authors';

        // Citations & Versions count (Null safe: Never show 0 if null, show "—")
        const citeCount = item.citations && item.citations.count !== null && item.citations.count !== undefined ? item.citations.count : null;
        const citeLink = item.citations && item.citations.link ? item.citations.link : '';
        const versCount = item.versions && item.versions.count !== null && item.versions.count !== undefined ? item.versions.count : null;
        const versLink = item.versions && item.versions.link ? item.versions.link : '';
        const clusterId = item.cluster_id || '';

        // Resources / PDFs
        let resourcesHtml = '';
        (item.resources || []).forEach(res => {
            if (res.link) {
                resourcesHtml += `<a href="${escapeHtml(res.link)}" target="_blank" class="btn-pdf-link">📥 [${escapeHtml(res.file_format || 'PDF')}] ${escapeHtml(res.title || 'Download')}</a>`;
            }
        });

        // Related link
        let relatedBtn = '';
        if (item.related_articles && item.related_articles.link) {
            relatedBtn = `<a href="${escapeHtml(item.related_articles.link)}" target="_blank" class="btn-action-secondary">🔗 Related Articles</a>`;
        }

        card.innerHTML = `
            <div class="scholar-card-header">
                <span class="scholar-pos">#${item.position !== undefined ? item.position + 1 : idx + 1}</span>
                <a href="${escapeHtml(item.link || '#')}" target="_blank" class="scholar-card-title">${escapeHtml(item.title)}</a>
            </div>
            <div class="scholar-card-authors" style="margin-top: 0.35rem; font-size: 0.85rem;">${authorsArr}</div>
            <div class="scholar-card-pub text-muted" style="font-size: 0.8rem; margin-top: 0.2rem;">📖 ${escapeHtml(item.publication ? item.publication.summary : '')}</div>
            ${item.snippet ? `<div class="scholar-card-snippet" style="margin-top: 0.4rem; font-size: 0.85rem; line-height: 1.4; color: var(--text-main);">"${escapeHtml(item.snippet)}"</div>` : ''}
            
            <div class="scholar-card-footer" style="margin-top: 0.6rem; display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                ${citeCount !== null ? (citeLink ? `<a href="${escapeHtml(citeLink)}" target="_blank" class="badge-citation-link">📊 Citations: ${citeCount.toLocaleString()}</a>` : `<span class="badge-citation">📊 Citations: ${citeCount.toLocaleString()}</span>`) : '<span class="badge-citation text-muted">📊 Citations: —</span>'}
                ${versCount !== null ? (versLink ? `<a href="${escapeHtml(versLink)}" target="_blank" class="badge-versions-link">📑 Versions: ${versCount}</a>` : `<span class="badge-versions">📑 Versions: ${versCount}</span>`) : ''}
                ${resourcesHtml}
                ${clusterId ? `<button class="btn-action-primary" onclick="openCitationsExplorerModal('${escapeHtml(clusterId)}', '${escapeHtml(item.title)}')">🔍 View Citations</button>` : ''}
                ${relatedBtn}
                <a href="${escapeHtml(item.link || '#')}" target="_blank" class="btn-scholar-ref">🎓 Scholar Link</a>
            </div>
        `;
        listEl.appendChild(card);
    });
}

// ==========================================
// PAPER PROFILE MODAL LOGIC (7 TABS)
// ==========================================
function openPaperModal(refId, fallbackRefObj = null) {
    openPaperModalToTab(refId, 'overview', fallbackRefObj);
}

function openPaperModalToTab(refId, tabName = 'overview', fallbackRefObj = null) {
    const modal = document.getElementById('paper-modal');
    modal.style.display = 'flex';
    switchPaperTab(tabName);

    fetch(`/references/${encodeURIComponent(refId)}`)
        .then(res => {
            if (!res.ok) {
                if (fallbackRefObj) return fallbackRefObj.master_record || fallbackRefObj;
                throw new Error('Reference record not found');
            }
            return res.json();
        })
        .then(master => {
            currentPaperRecord = master;
            populatePaperModal(master);
        })
        .catch(err => {
            console.warn('Loading paper modal with fallback:', err);
            const fallback = fallbackRefObj ? (fallbackRefObj.master_record || fallbackRefObj) : { reference_id: refId };
            currentPaperRecord = fallback;
            populatePaperModal(fallback);
        });
}

function closePaperModal() {
    document.getElementById('paper-modal').style.display = 'none';
}

function switchPaperTab(tabName) {
    document.querySelectorAll('.paper-tab-header .tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.paper-tab-content').forEach(content => content.classList.remove('active'));

    const btn = document.getElementById(`tab-paper-${tabName}-btn`);
    const content = document.getElementById(`paper-tab-${tabName}`);
    if (btn) btn.classList.add('active');
    if (content) content.classList.add('active');
}

function populatePaperModal(master) {
    if (!master) return;

    const canonical = master.canonical || {};
    const inputParsed = (master.input && master.input.parsed) || {};
    const titleVal = (canonical.title && canonical.title.value) || master.title || inputParsed.title || 'Untitled Reference';
    const yearVal = (canonical.year && canonical.year.value) || master.year || inputParsed.year || null;
    const venueVal = (canonical.venue && canonical.venue.value) || master.journal || inputParsed.journal || null;
    const typeVal = (canonical.reference_type && canonical.reference_type.value) || inputParsed.reference_type || 'journal-article';
    const pubVal = (canonical.publisher && canonical.publisher.value) || inputParsed.publisher || null;
    const vol = canonical.volume || inputParsed.volume || null;
    const iss = canonical.issue || inputParsed.issue || null;
    const pgs = canonical.pages || inputParsed.pages || null;
    const abstractVal = canonical.abstract || master.abstract || '';
    const doiVal = (canonical.identifiers && canonical.identifiers.doi && canonical.identifiers.doi.value) || master.doi || inputParsed.doi || null;
    const arxivVal = (canonical.identifiers && canonical.identifiers.arxiv_id && canonical.identifiers.arxiv_id.value) || master.arxiv_id || inputParsed.arxiv_id || null;
    const isbnVal = (canonical.identifiers && canonical.identifiers.isbn && canonical.identifiers.isbn.value) || inputParsed.isbn || null;
    const openalexId = (canonical.identifiers && canonical.identifiers.openalex_id && canonical.identifiers.openalex_id.value) || null;
    
    const sources = master.sources || {};
    const scholarSource = sources.google_scholar || {};
    const scholarData = scholarSource.data || {};
    const clusterId = (canonical.identifiers && canonical.identifiers.google_scholar_cluster_id && canonical.identifiers.google_scholar_cluster_id.value) || (scholarData && scholarData.cluster_id) || '';
    const scholarResultUrl = (canonical.identifiers && canonical.identifiers.google_scholar_url && canonical.identifiers.google_scholar_url.value) || master.scholar_url || (scholarData && scholarData.link) || `https://scholar.google.com/scholar?q=${encodeURIComponent(titleVal)}`;
    const paperUrl = canonical.url || master.url || '';

    // Modal Header Title & Subtitle
    document.getElementById('paper-modal-title').textContent = titleVal;
    
    let typeLabel = 'ARTICLE';
    let typeClass = 'badge-type-article';
    let shortType = 'Article';
    if (typeVal === 'proceedings-article') {
        typeLabel = 'CONFERENCE PROCEEDINGS';
        typeClass = 'badge-type-conference';
        shortType = 'Conference Paper';
    } else if (typeVal === 'book') {
        typeLabel = 'BOOK';
        typeClass = 'badge-type-book';
        shortType = 'Book';
    } else if (typeVal === 'book-chapter') {
        typeLabel = 'BOOK CHAPTER';
        typeClass = 'badge-type-chapter';
        shortType = 'Book Chapter';
    } else if (typeVal === 'preprint') {
        typeLabel = 'PREPRINT';
        typeClass = 'badge-type-preprint';
        shortType = 'Preprint';
    }

    const typeBadge = document.getElementById('paper-modal-badge-type');
    if (typeBadge) {
        typeBadge.textContent = typeLabel;
        typeBadge.className = `badge-ref-type ${typeClass}`;
    }

    const canAuthors = master.canonical_authors || [];
    const firstAuthor = canAuthors.length > 0 ? (canAuthors[0].family || canAuthors[0].name.split(' ').pop() || canAuthors[0].name) : '';
    const authorsEtAl = canAuthors.length > 1 ? `${firstAuthor} et al.` : firstAuthor;
    
    let subtitleParts = [];
    if (authorsEtAl) subtitleParts.push(authorsEtAl);
    if (yearVal) subtitleParts.push(String(yearVal));
    if (shortType) subtitleParts.push(shortType);
    if (venueVal) subtitleParts.push(venueVal);

    document.getElementById('paper-modal-subtitle').textContent = subtitleParts.join(' · ') || 'Academic Reference Profile';

    // Header Action Buttons
    const headerScholarLink = document.getElementById('modal-header-link-scholar');
    if (headerScholarLink) {
        headerScholarLink.href = scholarResultUrl;
    }

    const headerPdfLink = document.getElementById('modal-header-link-pdf');
    let directPdf = '';
    if (scholarData && Array.isArray(scholarData.resources)) {
        const pdfRes = scholarData.resources.find(r => (r.file_format || '').toLowerCase() === 'pdf' || (r.link || '').endsWith('.pdf'));
        if (pdfRes && pdfRes.link) directPdf = pdfRes.link;
    }
    if (!directPdf && paperUrl && paperUrl.endsWith('.pdf')) directPdf = paperUrl;

    if (headerPdfLink) {
        if (directPdf) {
            headerPdfLink.style.display = 'inline-flex';
            headerPdfLink.href = directPdf;
        } else {
            headerPdfLink.style.display = 'none';
        }
    }

    // TAB 1: OVERVIEW
    // 1. Academic Summary Details
    document.getElementById('paper-detail-original').textContent = (master.input && master.input.original_text) || master.original_text || '—';
    document.getElementById('paper-detail-venue').textContent = venueVal || '—';
    document.getElementById('paper-detail-year').textContent = yearVal || '—';
    
    const venueLabel = document.getElementById('paper-detail-venue-label');
    if (venueLabel) {
        venueLabel.textContent = typeVal === 'book' ? 'Book Container:' : (typeVal === 'book-chapter' ? 'Book Title:' : 'Venue / Conference:');
    }

    const typeDetail = document.getElementById('paper-detail-type');
    if (typeDetail) {
        typeDetail.textContent = typeLabel;
        typeDetail.className = `badge-ref-type ${typeClass}`;
    }

    // Publisher
    const pubItem = document.getElementById('paper-detail-publisher-item');
    const pubEl = document.getElementById('paper-detail-publisher');
    if (pubVal && pubItem && pubEl) {
        pubItem.style.display = 'block';
        pubEl.textContent = pubVal;
    } else if (pubItem) {
        pubItem.style.display = 'none';
    }

    // Volume, Issue, Pages
    const vipItem = document.getElementById('paper-detail-vip-item');
    const vipEl = document.getElementById('paper-detail-vip');
    if ((vol || iss || pgs) && vipItem && vipEl) {
        vipItem.style.display = 'block';
        let parts = [];
        if (vol) parts.push(`Vol. ${vol}`);
        if (iss) parts.push(`No. ${iss}`);
        if (pgs) parts.push(`pp. ${pgs}`);
        vipEl.textContent = parts.join(', ');
    } else if (vipItem) {
        vipItem.style.display = 'none';
    }

    // ISBN
    const isbnItem = document.getElementById('paper-detail-isbn-item');
    const isbnEl = document.getElementById('paper-detail-isbn');
    if (isbnVal && isbnItem && isbnEl) {
        isbnItem.style.display = 'block';
        isbnEl.textContent = isbnVal;
    } else if (isbnItem) {
        isbnItem.style.display = 'none';
    }

    const absBox = document.getElementById('paper-detail-abstract-box');
    if (abstractVal) {
        absBox.style.display = 'block';
        document.getElementById('paper-detail-abstract').textContent = abstractVal;
    } else {
        absBox.style.display = 'none';
    }

    // 2. Overview Authors Summary Chips
    const overviewAuthorsContainer = document.getElementById('overview-authors-summary-chips');
    overviewAuthorsContainer.innerHTML = '';
    canAuthors.forEach(a => {
        const aName = a.name || 'Author';
        const aId = (a.identifiers && (a.identifiers.openalex_id || a.identifiers.google_scholar_id)) || '';
        const initials = aName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'A';
        
        const chip = document.createElement('div');
        chip.className = 'author-chip';
        chip.innerHTML = `
            <span class="author-avatar">${initials}</span>
            <span class="author-name">${escapeHtml(aName)}</span>
        `;
        chip.onclick = () => openAuthorProfile(aId, aName);
        overviewAuthorsContainer.appendChild(chip);
    });

    // 3. Multi-Source Citations (Never show 0 when null)
    const citeCounts = canonical.citation_counts || {};
    const scholarCite = citeCounts.google_scholar;
    const alexCite = citeCounts.openalex;
    const crossCite = citeCounts.crossref;
    const canonicalCite = citeCounts.canonical_value;

    document.getElementById('paper-cite-scholar').textContent = scholarCite !== null && scholarCite !== undefined ? scholarCite.toLocaleString() : '—';
    document.getElementById('paper-cite-openalex').textContent = alexCite !== null && alexCite !== undefined ? alexCite.toLocaleString() : '—';
    document.getElementById('paper-cite-crossref').textContent = crossCite !== null && crossCite !== undefined ? crossCite.toLocaleString() : '—';
    document.getElementById('paper-cite-canonical').textContent = canonicalCite !== null && canonicalCite !== undefined ? canonicalCite.toLocaleString() : '—';

    document.getElementById('paper-status-scholar').textContent = sources.google_scholar && sources.google_scholar.available ? (sources.google_scholar.matched ? '✓ Matched' : 'Available') : 'Unavailable';
    document.getElementById('paper-status-openalex').textContent = sources.openalex && sources.openalex.matched ? '✓ Matched' : (sources.openalex && sources.openalex.available ? 'Available' : 'Unavailable');
    document.getElementById('paper-status-crossref').textContent = sources.crossref && sources.crossref.matched ? '✓ Matched' : (sources.crossref && sources.crossref.available ? 'Available' : 'Unavailable');

    // Header Citations Button
    const headerCitesBtn = document.getElementById('modal-header-btn-cites');
    if (headerCitesBtn) {
        if (scholarCite !== null && scholarCite !== undefined) {
            headerCitesBtn.textContent = `📊 Citations · ${scholarCite.toLocaleString()}`;
        } else if (canonicalCite !== null && canonicalCite !== undefined) {
            headerCitesBtn.textContent = `📊 Citations · ${canonicalCite.toLocaleString()}`;
        } else {
            headerCitesBtn.textContent = '📊 Citations';
        }
    }

    // 4. Identifiers Grid Section
    const idsGrid = document.getElementById('paper-identifiers-grid');
    idsGrid.innerHTML = '';
    const doiVerif = master.doi_verification || {};
    
    const idItems = [
        { name: 'DOI', val: doiVal, link: doiVal ? `https://doi.org/${doiVal}` : null, status: doiVerif.status || 'unverified' },
        { name: 'OpenAlex ID', val: openalexId, link: openalexId, status: openalexId ? 'verified' : 'unverified' },
        { name: 'Scholar Cluster ID', val: clusterId || null, link: clusterId ? `https://scholar.google.com/scholar?cites=${clusterId}` : null, status: clusterId ? 'verified' : 'unverified' },
        { name: 'arXiv ID', val: arxivVal, link: arxivVal ? `https://arxiv.org/abs/${arxivVal}` : null, status: arxivVal ? 'verified' : 'unverified' },
        { name: 'ISBN', val: isbnVal, link: null, status: isbnVal ? 'verified' : 'unverified' }
    ];

    idItems.forEach(idItem => {
        const idCard = document.createElement('div');
        idCard.className = 'identifier-card';
        
        let valHtml = '<span class="text-muted">—</span>';
        if (idItem.val) {
            if (idItem.link) {
                valHtml = `<a href="${escapeHtml(idItem.link)}" target="_blank" class="identifier-link">${escapeHtml(idItem.val)}</a>`;
            } else {
                valHtml = `<span class="identifier-val">${escapeHtml(idItem.val)}</span>`;
            }
        }

        let statusBadge = `<span class="badge-status badge-status-${idItem.status}">${idItem.status}</span>`;

        idCard.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                <span class="identifier-name">${escapeHtml(idItem.name)}</span>
                ${statusBadge}
            </div>
            <div>${valHtml}</div>
        `;
        idsGrid.appendChild(idCard);
    });

    // 5. Source Comparison Status Table
    const tableBody = document.getElementById('sources-table-body');
    tableBody.innerHTML = '';
    
    const tableSources = [
        { name: 'OpenAlex', key: 'openalex', tab: 'openalex', cite: alexCite },
        { name: 'Crossref', key: 'crossref', tab: 'crossref', cite: crossCite },
        { name: 'Google Scholar', key: 'google_scholar', tab: 'scholar', cite: scholarCite }
    ];

    tableSources.forEach(s => {
        const srcObj = sources[s.key] || {};
        const isAvail = srcObj.available || false;
        const isMatched = srcObj.matched || false;
        const sData = srcObj.data || {};
        
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${s.name}</strong></td>
            <td><span class="badge-status ${isMatched ? 'badge-status-verified' : (isAvail ? 'badge-status-unverified' : 'badge-status-conflict')}">${isMatched ? '✓ Matched' : (isAvail ? 'Available' : 'Unavailable')}</span></td>
            <td>${isMatched ? '✓ ' + escapeHtml((sData.title || titleVal).substring(0, 45) + '...') : '<span class="text-muted">—</span>'}</td>
            <td>${isMatched ? '✓ Identified' : '<span class="text-muted">—</span>'}</td>
            <td>${s.cite !== null && s.cite !== undefined ? s.cite.toLocaleString() : '<span class="text-muted">—</span>'}</td>
            <td><button class="btn-action-secondary" style="font-size: 0.75rem; padding: 0.15rem 0.5rem;" onclick="switchPaperTab('${s.tab}')">Inspect</button></td>
        `;
        tableBody.appendChild(row);
    });

    // 6. DOI Verification Status Box
    const doiSection = document.getElementById('paper-doi-section');
    const conflicts = (master.quality_and_conflicts && master.quality_and_conflicts.conflicts) || [];

    if (doiVerif.status === 'verified') {
        doiSection.innerHTML = `
            <div class="doi-box doi-box-verified">
                <span class="doi-icon">✓</span>
                <div>
                    <div style="font-weight: 600; color: var(--success-color);">Verified Canonical DOI</div>
                    <div style="font-size: 0.85rem; margin-top: 0.15rem;">
                        <a href="https://doi.org/${escapeHtml(doiVerif.canonical_doi)}" target="_blank" style="color: var(--success-color); font-weight: 500;">https://doi.org/${escapeHtml(doiVerif.canonical_doi)}</a>
                        ${doiVerif.reconciled_with_arxiv ? ' <span class="badge-matched">(Reconciled with official arXiv deposit)</span>' : ''}
                    </div>
                </div>
            </div>
        `;
    } else if (doiVerif.status === 'conflict' || conflicts.length > 0) {
        let conflictsHtml = '';
        conflicts.forEach(c => {
            conflictsHtml += `
                <div class="conflict-item">
                    <strong>Rejected ${escapeHtml(c.field)}:</strong> <code>${escapeHtml(c.rejected_value)}</code> (${escapeHtml(c.provider)})<br>
                    <span class="text-muted">Reason: ${escapeHtml(c.reason)}</span>
                </div>
            `;
        });
        doiSection.innerHTML = `
            <div class="doi-box doi-box-conflict">
                <span class="doi-icon">⚠️</span>
                <div style="width: 100%;">
                    <div style="font-weight: 600; color: #f87171;">Conflicting Metadata Excluded</div>
                    <div style="font-size: 0.84rem; margin-top: 0.15rem; color: var(--text-secondary);">
                        The DOI or venue returned by third-party deposits failed strict consistency checks and was excluded from canonical fields.
                    </div>
                    ${conflictsHtml}
                </div>
            </div>
        `;
    } else {
        doiSection.innerHTML = `
            <div class="doi-box doi-box-unverified">
                <span class="doi-icon">ℹ️</span>
                <div>
                    <div style="font-weight: 600;">No Official DOI Registered</div>
                    <div style="font-size: 0.82rem; color: var(--text-secondary);">This reference does not contain a verified DOI identifier.</div>
                </div>
            </div>
        `;
    }

    // TAB 2: AUTHORS (FIRST-CLASS INTERACTIVE CARDS)
    const authorsContainer = document.getElementById('paper-authors-list');
    authorsContainer.innerHTML = '';
    if (canAuthors.length === 0) {
        authorsContainer.innerHTML = '<div class="text-muted" style="padding: 1.5rem; text-align: center;">No individual authors indexed for this reference.</div>';
    } else {
        canAuthors.forEach(a => {
            const aName = a.name || 'Author';
            const aGiven = a.given || '';
            const aFamily = a.family || '';
            const aId = (a.identifiers && (a.identifiers.openalex_id || a.identifiers.google_scholar_id)) || '';
            const openalexAuthorId = a.identifiers && a.identifiers.openalex_id;
            const scholarAuthorId = a.identifiers && a.identifiers.google_scholar_id;
            const orcid = a.identifiers && a.identifiers.orcid;
            const initials = aName.split(' ').filter(Boolean).map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'A';

            let idBadges = [];
            if (openalexAuthorId) {
                idBadges.push(`<a href="${escapeHtml(openalexAuthorId)}" target="_blank" class="badge-source-link" onclick="event.stopPropagation();">🌐 OpenAlex Profile</a>`);
            }
            if (scholarAuthorId) {
                idBadges.push(`<a href="https://scholar.google.com/citations?user=${escapeHtml(scholarAuthorId)}" target="_blank" class="btn-scholar-ref" style="font-size: 0.75rem; padding: 0.2rem 0.5rem;" onclick="event.stopPropagation();">🎓 Scholar Profile</a>`);
            }
            if (orcid) {
                idBadges.push(`<a href="https://orcid.org/${escapeHtml(orcid)}" target="_blank" class="badge-orcid-link" onclick="event.stopPropagation();">🆔 ORCID: ${escapeHtml(orcid)}</a>`);
            }

            const authorCard = document.createElement('div');
            authorCard.className = 'author-full-card glass-panel';
            authorCard.innerHTML = `
                <div class="author-full-header">
                    <div class="author-avatar-large">${initials}</div>
                    <div style="flex: 1;">
                        <h4 class="author-full-name">${escapeHtml(aName)}</h4>
                        ${(aGiven || aFamily) ? `<div class="text-muted" style="font-size: 0.8rem;">Given: ${escapeHtml(aGiven || '—')} • Family: ${escapeHtml(aFamily || '—')}</div>` : ''}
                    </div>
                </div>
                ${idBadges.length > 0 ? `<div class="author-id-badges-row">${idBadges.join(' ')}</div>` : ''}
                <div style="margin-top: 0.75rem;">
                    <button class="btn-action-primary" style="width: 100%; justify-content: center;" onclick="openAuthorProfile('${escapeHtml(aId)}', '${escapeHtml(aName)}')">👤 View Author Profile</button>
                </div>
            `;
            authorsContainer.appendChild(authorCard);
        });
    }

    // TAB 3: CITATIONS SETUP
    setupPaperCitationsTab(clusterId, openalexId, titleVal, alexCite || scholarCite || canonicalCite);

    // TAB 4: GOOGLE SCHOLAR
    const scholarContainer = document.getElementById('paper-scholar-content');
    if (!scholarSource.available) {
        scholarContainer.innerHTML = `
            <div class="scholar-fallback-banner" style="margin: 1rem 0;">
                <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem;">🎓 Google Scholar data unavailable</div>
                <div style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.85rem;">Google Scholar integration is not configured. You can still search this paper directly on Google Scholar:</div>
                <a href="${scholarResultUrl}" target="_blank" class="btn-scholar-ref" style="display: inline-block;">🎓 Search on Google Scholar</a>
            </div>
        `;
    } else {
        const sPub = scholarData.publication || {};
        const sCites = scholarData.citations || {};
        const sVers = scholarData.versions || {};

        let resourcesHtml = '';
        (scholarData.resources || []).forEach(r => {
            resourcesHtml += `<a href="${escapeHtml(r.link)}" target="_blank" class="btn-pdf-link">📥 [${escapeHtml(r.file_format || 'PDF')}] ${escapeHtml(r.title)}</a> `;
        });

        scholarContainer.innerHTML = `
            <div class="scholar-card glass-panel" style="margin: 0.5rem 0;">
                <div class="scholar-card-title" style="font-size: 1.15rem;">📄 ${escapeHtml(scholarData.title || titleVal)}</div>
                <div class="text-muted" style="font-size: 0.85rem; margin-top: 0.3rem;">📖 ${escapeHtml(sPub.summary || venueVal || 'Google Scholar Index')}</div>
                ${scholarData.snippet ? `<div style="margin-top: 0.5rem; font-size: 0.88rem; line-height: 1.5; color: var(--text-main); font-style: italic;">"${escapeHtml(scholarData.snippet)}"</div>` : ''}
                
                <div style="margin-top: 1rem; display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    <a href="${escapeHtml(scholarData.link || scholarResultUrl)}" target="_blank" class="btn-scholar-ref">🎓 Open Scholar</a>
                    ${sCites.count !== null && sCites.count !== undefined ? `<a href="${escapeHtml(sCites.link || `https://scholar.google.com/scholar?cites=${clusterId}`)}" target="_blank" class="badge-citation-link">📊 Cited by ${sCites.count.toLocaleString()}</a>` : '<span class="badge-citation text-muted">📊 Citations: Not available</span>'}
                    ${sVers.count !== null && sVers.count !== undefined ? `<a href="${escapeHtml(sVers.link || '#')}" target="_blank" class="badge-versions-link">📑 ${sVers.count} Versions</a>` : ''}
                    ${resourcesHtml}
                    ${clusterId ? `<button class="btn-action-primary" onclick="exploreCitationsFromScholar('${escapeHtml(clusterId)}')">🔍 View Cited By</button>` : ''}
                </div>
            </div>
        `;
    }

    // TAB 5: OPENALEX
    const openalexContainer = document.getElementById('paper-openalex-content');
    const alexSource = sources.openalex || {};
    const alexData = alexSource.data || {};
    openalexContainer.innerHTML = `
        <div class="glass-panel" style="padding: 1.25rem;">
            <div style="font-weight: 600; font-size: 1.05rem; color: var(--text-main);">🌐 OpenAlex Metadata Record</div>
            <div style="margin-top: 0.75rem; font-size: 0.88rem; line-height: 1.6;">
                <strong>Work ID:</strong> ${alexData.openalex_id ? `<a href="${escapeHtml(alexData.openalex_id)}" target="_blank" style="color: var(--secondary-color); font-weight: 500;">${escapeHtml(alexData.openalex_id)}</a>` : 'Not available'}<br>
                <strong>Title:</strong> ${escapeHtml(alexData.title || 'Not available')}<br>
                <strong>Venue / Source:</strong> ${escapeHtml(alexData.journal || 'Not available')}<br>
                <strong>Citations Count:</strong> ${alexData.citation_count !== undefined && alexData.citation_count !== null ? alexData.citation_count.toLocaleString() : 'Not available'}<br>
                <strong>Raw Storage File:</strong> <code style="font-size: 0.78rem;">${escapeHtml(alexSource.raw_file || 'Not stored')}</code>
            </div>
        </div>
    `;

    // TAB 6: CROSSREF
    const crossrefContainer = document.getElementById('paper-crossref-content');
    const crossSource = sources.crossref || {};
    const crossData = crossSource.data || {};
    crossrefContainer.innerHTML = `
        <div class="glass-panel" style="padding: 1.25rem;">
            <div style="font-weight: 600; font-size: 1.05rem; color: var(--text-main);">🔗 Crossref Metadata Record</div>
            <div style="margin-top: 0.75rem; font-size: 0.88rem; line-height: 1.6;">
                <strong>DOI:</strong> ${crossData.doi ? `<a href="https://doi.org/${escapeHtml(crossData.doi)}" target="_blank" style="color: var(--primary-color); font-weight: 500;">${escapeHtml(crossData.doi)}</a>` : 'Not available'}<br>
                <strong>Title:</strong> ${escapeHtml(crossData.title || 'Not available')}<br>
                <strong>Container / Publisher:</strong> ${escapeHtml(crossData.journal || 'Not available')}<br>
                <strong>Citations Count:</strong> ${crossData.citation_count !== undefined && crossData.citation_count !== null ? crossData.citation_count.toLocaleString() : 'Not available'}<br>
                <strong>Raw Storage File:</strong> <code style="font-size: 0.78rem;">${escapeHtml(crossSource.raw_file || 'Not stored')}</code>
            </div>
        </div>
    `;

    // TAB 7: MASTER JSON
    document.getElementById('paper-raw-json-code').textContent = JSON.stringify(master, null, 2);
}

function copyPaperJson() {
    if (!currentPaperRecord) return;
    navigator.clipboard.writeText(JSON.stringify(currentPaperRecord, null, 2))
        .then(() => showToast('Master Record JSON copied to clipboard!', 'success'))
        .catch(err => console.error('Could not copy JSON:', err));
}

function downloadPaperJson() {
    if (!currentPaperRecord) return;
    const blob = new Blob([JSON.stringify(currentPaperRecord, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentPaperRecord.reference_id || 'reference'}_master.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('Master JSON downloaded.', 'info');
}

function copyCurrentPaperBibtex() {
    if (!currentPaperRecord) return;
    const can = currentPaperRecord.canonical || {};
    const title = (can.title && can.title.value) || currentPaperRecord.title || 'Untitled';
    const year = (can.year && can.year.value) || currentPaperRecord.year || '';
    const venue = (can.venue && can.venue.value) || currentPaperRecord.journal || '';
    const doi = (can.identifiers && can.identifiers.doi && can.identifiers.doi.value) || currentPaperRecord.doi || '';
    
    const authors = (currentPaperRecord.canonical_authors || []).map(a => a.name).join(' and ') || 'Unknown';
    
    let bib = `@article{ref_selected,\n  title = {${title}},\n  author = {${authors}},\n`;
    if (year) bib += `  year = {${year}},\n`;
    const invalidVenues = ['google scholar', 'openalex', 'crossref', 'serpapi', 'arxiv', 'none', 'unknown', 'n/a'];
    if (venue && !invalidVenues.includes(venue.trim().toLowerCase())) {
        bib += `  journal = {${venue.trim()}},\n`;
    }
    if (doi) bib += `  doi = {${doi}},\n`;
    bib += `}`;

    copyText(bib, 'BibTeX entry copied to clipboard!');
}

function copySingleRefBibtex(ref, idx = 1) {
    const master = ref.master_record || ref;
    const can = master.canonical || {};
    const title = (can.title && can.title.value) || ref.title || cleanRefQuery(ref.original_text || ref.text || '') || 'Untitled';
    const year = (can.year && can.year.value) || ref.year || '';
    const venue = (can.venue && can.venue.value) || ref.journal || '';
    const doi = (can.identifiers && can.identifiers.doi && can.identifiers.doi.value) || ref.doi || '';
    
    const authorsList = (master.canonical_authors && master.canonical_authors.length > 0)
        ? master.canonical_authors.map(a => a.name)
        : (Array.isArray(ref.authors) ? ref.authors.map(a => (typeof a === 'object' ? (a.name || '') : String(a))) : []);
    
    const authors = authorsList.filter(Boolean).join(' and ') || 'Unknown';
    
    let bib = `@article{ref_${idx},\n  title = {${title}},\n  author = {${authors}},\n`;
    if (year) bib += `  year = {${year}},\n`;
    const invalidVenues = ['google scholar', 'openalex', 'crossref', 'serpapi', 'arxiv', 'none', 'unknown', 'n/a'];
    if (venue && !invalidVenues.includes(venue.trim().toLowerCase())) {
        bib += `  journal = {${venue.trim()}},\n`;
    }
    if (doi) bib += `  doi = {${doi}},\n`;
    bib += `}`;

    copyText(bib, `BibTeX for reference #${idx} copied!`);
}

// ==========================================
// CITATIONS EXPLORATION LOGIC
// ==========================================
let currentPaperCitationPage = 1;
let currentPaperClusterId = '';
let currentPaperOpenAlexId = '';
let currentPaperCitationProvider = 'openalex';

function setupPaperCitationsTab(clusterId, openalexId, paperTitle, totalCitations = null) {
    currentPaperClusterId = clusterId || '';
    currentPaperOpenAlexId = openalexId ? openalexId.replace('https://openalex.org/', '').replace('http://openalex.org/', '') : '';
    currentPaperCitationPage = 1;
    currentPaperCitationProvider = currentPaperOpenAlexId ? 'openalex' : 'google_scholar';

    const listEl = document.getElementById('paper-citations-list');
    const infoEl = document.getElementById('paper-citations-count-info');
    const pagEl = document.getElementById('paper-citations-pagination');
    const tabTitleEl = document.getElementById('citations-tab-title');

    if (tabTitleEl) {
        if (totalCitations !== null && totalCitations !== undefined) {
            tabTitleEl.textContent = `📈 Cited By (${totalCitations.toLocaleString()} citations)`;
        } else {
            tabTitleEl.textContent = '📈 Cited By';
        }
    }

    if (!currentPaperOpenAlexId && !currentPaperClusterId) {
        infoEl.textContent = 'Citation index lookup';
        listEl.innerHTML = `
            <div class="scholar-fallback-banner" style="margin: 1rem 0;">
                <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem;">🎓 Citation Index Search</div>
                <div style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.85rem;">You can explore citing papers directly on Google Scholar:</div>
                <a href="https://scholar.google.com/scholar?q=${encodeURIComponent(paperTitle)}" target="_blank" class="btn-scholar-ref" style="display: inline-block;">🎓 Search Citations on Google Scholar</a>
            </div>
        `;
        pagEl.style.display = 'none';
        return;
    }

    loadPaperCitations(1);
}

function exploreCitationsFromScholar(clusterId) {
    currentPaperClusterId = clusterId;
    currentPaperCitationProvider = 'google_scholar';
    switchPaperTab('citations');
    loadPaperCitations(1);
}

function openCitationsExplorerModal(clusterId, title) {
    currentPaperClusterId = clusterId;
    currentPaperCitationProvider = 'google_scholar';
    const modal = document.getElementById('paper-modal');
    modal.style.display = 'flex';
    document.getElementById('paper-modal-title').textContent = title || 'Citing Publications';
    document.getElementById('paper-modal-subtitle').textContent = `Google Scholar Cluster ID: ${clusterId}`;
    switchPaperTab('citations');
    loadPaperCitations(1);
}

function loadPaperCitations(page = 1) {
    currentPaperCitationPage = page;
    const listEl = document.getElementById('paper-citations-list');
    const loadingEl = document.getElementById('paper-citations-loading');
    const pagEl = document.getElementById('paper-citations-pagination');
    const infoEl = document.getElementById('paper-citations-count-info');
    const prevBtn = document.getElementById('paper-cite-prev-btn');
    const nextBtn = document.getElementById('paper-cite-next-btn');
    const pageInfo = document.getElementById('paper-cite-page-info');

    loadingEl.style.display = 'block';
    listEl.innerHTML = '';

    if (currentPaperOpenAlexId && currentPaperCitationProvider === 'openalex') {
        fetch(`/openalex/citations/${encodeURIComponent(currentPaperOpenAlexId)}?page=${page}&num=10`)
            .then(res => res.json())
            .then(data => {
                loadingEl.style.display = 'none';
                const results = data.results || [];
                const totalCount = data.total_count || results.length;

                if (results.length === 0) {
                    listEl.innerHTML = '<div class="text-muted" style="padding: 1.5rem; text-align: center;">No citing publications recorded in OpenAlex.</div>';
                    pagEl.style.display = 'none';
                    return;
                }

                infoEl.textContent = `Showing page ${page} of ${totalCount.toLocaleString()} citing publications (via OpenAlex)`;
                renderOpenAlexCitationsToElement(results, listEl);
                pagEl.style.display = 'flex';
                pageInfo.textContent = `Page ${page}`;
                prevBtn.disabled = page <= 1;
                nextBtn.disabled = results.length < 10;
            })
            .catch(err => {
                console.error(err);
                loadingEl.style.display = 'none';
                listEl.innerHTML = '<div class="scholar-fallback-banner">⚠️ Error exploring citing papers from OpenAlex.</div>';
            });
    } else if (currentPaperClusterId) {
        fetch(`/scholar/citations/${encodeURIComponent(currentPaperClusterId)}?page=${page}&num=10`)
            .then(res => res.json())
            .then(data => {
                loadingEl.style.display = 'none';
                if (!data.available) {
                    listEl.innerHTML = `
                        <div class="scholar-fallback-banner" style="margin: 1rem 0;">
                            <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.35rem;">🎓 Google Scholar data unavailable</div>
                            <div style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 0.85rem;">Google Scholar API key (SerpApi) is not configured. You can still open citing articles directly on Google Scholar:</div>
                            <a href="${escapeHtml(data.scholar_url)}" target="_blank" class="btn-scholar-ref" style="display: inline-block;">🎓 Open Citing Papers on Google Scholar</a>
                        </div>
                    `;
                    pagEl.style.display = 'none';
                    return;
                }

                const results = data.results || [];
                if (results.length === 0) {
                    listEl.innerHTML = '<div class="text-muted" style="padding: 1.5rem; text-align: center;">No citing papers were returned.</div>';
                    pagEl.style.display = 'none';
                    return;
                }

                infoEl.textContent = `Showing page ${page} of citing publications (via Google Scholar)`;
                renderScholarSearchResultsToElement(results, listEl);
                pagEl.style.display = 'flex';
                pageInfo.textContent = `Page ${page}`;
                prevBtn.disabled = page <= 1;
                nextBtn.disabled = results.length < 10;
            })
            .catch(err => {
                console.error(err);
                loadingEl.style.display = 'none';
                listEl.innerHTML = '<div class="scholar-fallback-banner">⚠️ Error exploring citing papers. Please try again.</div>';
            });
    }
}

function changePaperCitationsPage(delta) {
    const newPage = currentPaperCitationPage + delta;
    if (newPage >= 1) {
        loadPaperCitations(newPage);
    }
}

function renderOpenAlexCitationsToElement(results, container) {
    container.innerHTML = '';
    results.forEach((item, idx) => {
        const card = document.createElement('div');
        card.className = 'scholar-card glass-panel';

        const authorsArr = (item.authors || []).map(a => typeof a === 'object' ? (a.name || a.display_name || '') : String(a)).filter(Boolean).join(', ') || 'Authors not listed';
        const citeCount = item.citation_count !== undefined ? item.citation_count : null;
        const doiVal = item.doi ? item.doi.replace('https://doi.org/', '').replace('http://doi.org/', '') : '';
        const pdfUrl = item.pdf_url || '';

        card.innerHTML = `
            <div class="scholar-card-header">
                <span class="scholar-pos">#${idx + 1}</span>
                <a href="${escapeHtml(item.url || (doiVal ? `https://doi.org/${doiVal}` : '#'))}" target="_blank" class="scholar-card-title">${escapeHtml(item.title)}</a>
            </div>
            <div class="scholar-card-authors" style="margin-top: 0.35rem; font-size: 0.85rem; color: var(--text-secondary);">👥 ${escapeHtml(authorsArr)}</div>
            <div class="scholar-card-pub text-muted" style="font-size: 0.8rem; margin-top: 0.2rem;">📖 ${escapeHtml(item.journal || item.venue || 'Academic Publication')} • 📅 ${item.year || '—'}</div>
            ${item.abstract ? `<div class="scholar-card-snippet" style="margin-top: 0.4rem; font-size: 0.85rem; line-height: 1.4; color: var(--text-main);">"${escapeHtml(item.abstract.substring(0, 180))}..."</div>` : ''}

            <div class="scholar-card-footer" style="margin-top: 0.6rem; display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                ${citeCount !== null ? `<span class="badge-citation">📊 ${citeCount.toLocaleString()} citations</span>` : '<span class="badge-citation text-muted">📊 Citations: —</span>'}
                ${doiVal ? `<a href="https://doi.org/${escapeHtml(doiVal)}" target="_blank" class="badge-id badge-id-doi">🔗 DOI: ${escapeHtml(doiVal)}</a>` : ''}
                ${pdfUrl ? `<a href="${escapeHtml(pdfUrl)}" target="_blank" class="btn-pdf-link">📄 Direct PDF</a>` : ''}
                <a href="https://scholar.google.com/scholar?q=${encodeURIComponent(item.title)}" target="_blank" class="btn-scholar-ref">🎓 Scholar</a>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderScholarSearchResultsToElement(results, container) {
    container.innerHTML = '';
    results.forEach((item, idx) => {
        const card = document.createElement('div');
        card.className = 'scholar-card glass-panel';

        const authorsArr = (item.authors || []).map(a => {
            if (a.author_id) {
                return `<span class="author-link-chip" onclick="openAuthorProfile('${escapeHtml(a.author_id)}', '${escapeHtml(a.name)}')">👤 ${escapeHtml(a.name)}</span>`;
            }
            return `<span class="text-muted">${escapeHtml(a.name)}</span>`;
        }).join(', ') || 'Unknown Authors';

        const citeCount = item.citations && item.citations.count !== null && item.citations.count !== undefined ? item.citations.count : null;
        const citeLink = item.citations && item.citations.link ? item.citations.link : '';

        // Resources / PDFs
        let resourcesHtml = '';
        (item.resources || []).forEach(res => {
            if (res.link) {
                resourcesHtml += `<a href="${escapeHtml(res.link)}" target="_blank" class="btn-pdf-link">📄 [${escapeHtml(res.file_format || 'PDF')}]</a>`;
            }
        });

        card.innerHTML = `
            <div class="scholar-card-header">
                <span class="scholar-pos">#${item.position !== undefined ? item.position + 1 : idx + 1}</span>
                <a href="${escapeHtml(item.link || '#')}" target="_blank" class="scholar-card-title">${escapeHtml(item.title)}</a>
            </div>
            <div class="scholar-card-authors" style="margin-top: 0.35rem; font-size: 0.85rem;">${authorsArr}</div>
            <div class="scholar-card-pub text-muted" style="font-size: 0.8rem; margin-top: 0.2rem;">📖 ${escapeHtml(item.publication ? item.publication.summary : '')}</div>
            ${item.snippet ? `<div class="scholar-card-snippet" style="margin-top: 0.4rem; font-size: 0.85rem; line-height: 1.4; color: var(--text-main);">"${escapeHtml(item.snippet)}"</div>` : ''}
            
            <div class="scholar-card-footer" style="margin-top: 0.6rem; display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap;">
                ${citeCount !== null ? (citeLink ? `<a href="${escapeHtml(citeLink)}" target="_blank" class="badge-citation-link">📊 ${citeCount.toLocaleString()} citations</a>` : `<span class="badge-citation">📊 ${citeCount.toLocaleString()} citations</span>`) : '<span class="badge-citation text-muted">📊 Citations: —</span>'}
                ${resourcesHtml}
                <a href="${escapeHtml(item.link || '#')}" target="_blank" class="btn-scholar-ref">🎓 Scholar</a>
                <button class="btn-action-secondary" style="font-size: 0.75rem; padding: 0.2rem 0.5rem;" onclick="searchPaperOnScholar('${escapeHtml(item.title)}')">🔎 Search Paper</button>
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// AUTHOR PROFILE MODAL LOGIC
// ==========================================
let currentAuthorId = '';
let currentAuthorName = '';
let currentAuthorProvider = 'openalex';
let currentAuthorPage = 1;
let currentAuthorTotalPages = 1;

function switchAuthorProvider(prov) {
    currentAuthorProvider = prov;
    const alexBtn = document.getElementById('prov-openalex-btn');
    const scholarBtn = document.getElementById('prov-scholar-btn');
    if (alexBtn) alexBtn.classList.toggle('active', prov === 'openalex');
    if (scholarBtn) scholarBtn.classList.toggle('active', prov === 'google_scholar');
    
    fetchAuthorProfileAndWorks();
}

function openAuthorProfile(authorId, fallbackName = '') {
    if (!authorId && !fallbackName) return;
    
    currentAuthorId = authorId || fallbackName;
    currentAuthorName = fallbackName || authorId;
    currentAuthorPage = 1;
    currentAuthorProvider = 'openalex';
    
    const modal = document.getElementById('author-modal');
    modal.style.display = 'flex';
    
    const alexBtn = document.getElementById('prov-openalex-btn');
    const scholarBtn = document.getElementById('prov-scholar-btn');
    if (alexBtn) alexBtn.classList.add('active');
    if (scholarBtn) scholarBtn.classList.remove('active');
    
    fetchAuthorProfileAndWorks();
}

function fetchAuthorProfileAndWorks() {
    const fallbackName = currentAuthorName;
    const authorId = currentAuthorId;
    
    document.getElementById('author-profile-name').textContent = fallbackName || 'Loading Author Profile...';
    document.getElementById('author-profile-affil').textContent = '';
    document.getElementById('author-kpi-works').textContent = '-';
    document.getElementById('author-kpi-citations').textContent = '-';
    document.getElementById('author-kpi-hindex').textContent = '-';
    document.getElementById('author-kpi-i10index').textContent = '-';
    document.getElementById('author-topics-section').style.display = 'none';
    document.getElementById('author-works-list').innerHTML = '';
    document.getElementById('author-works-loading').style.display = 'block';
    
    const scholarLink = document.getElementById('author-scholar-link');
    const openalexLink = document.getElementById('author-openalex-link');
    const orcidLink = document.getElementById('author-orcid-link');

    const encodedSearchName = encodeURIComponent(fallbackName || authorId);
    if (scholarLink) {
        scholarLink.style.display = 'inline-flex';
        scholarLink.href = `https://scholar.google.com/scholar?q=author:%22${encodedSearchName}%22`;
    }
    
    const cleanId = authorId.replace('https://openalex.org/', '').replace('http://openalex.org/', '');
    
    if (openalexLink && (authorId.startsWith('A') || authorId.includes('openalex.org'))) {
        openalexLink.style.display = 'inline-flex';
        openalexLink.href = `https://openalex.org/${cleanId}`;
    } else if (openalexLink) {
        openalexLink.style.display = 'none';
    }

    fetch(`/authors/${encodeURIComponent(cleanId)}?provider=${currentAuthorProvider}`)
        .then(res => {
            if (!res.ok) throw new Error('Author profile query failed');
            return res.json();
        })
        .then(data => {
            document.getElementById('author-profile-name').textContent = data.display_name || data.name || fallbackName;
            
            if (data.scholar_url && scholarLink) {
                scholarLink.href = data.scholar_url;
            }

            if (data.orcid && orcidLink) {
                orcidLink.style.display = 'inline-flex';
                orcidLink.href = `https://orcid.org/${data.orcid}`;
            } else if (orcidLink) {
                orcidLink.style.display = 'none';
            }
            
            if (data.affiliations && data.affiliations.length > 0) {
                document.getElementById('author-profile-affil').textContent = '📍 ' + data.affiliations.join(' • ');
            } else {
                document.getElementById('author-profile-affil').textContent = '';
            }
            
            document.getElementById('author-kpi-works').textContent = data.works_count !== undefined && data.works_count !== null ? data.works_count : '—';
            document.getElementById('author-kpi-citations').textContent = data.cited_by_count !== undefined && data.cited_by_count !== null ? data.cited_by_count.toLocaleString() : '—';
            document.getElementById('author-kpi-hindex').textContent = data.h_index !== undefined && data.h_index !== null ? data.h_index : '—';
            document.getElementById('author-kpi-i10index').textContent = data.i10_index !== undefined && data.i10_index !== null ? data.i10_index : '—';
            
            if (data.topics && data.topics.length > 0) {
                const topicsSec = document.getElementById('author-topics-section');
                const topicsContainer = document.getElementById('author-topics-container');
                topicsSec.style.display = 'block';
                topicsContainer.innerHTML = '';
                data.topics.forEach(top => {
                    const tag = document.createElement('span');
                    tag.className = 'keyword-pill';
                    tag.textContent = top;
                    topicsContainer.appendChild(tag);
                });
            }
        })
        .catch(err => {
            console.warn("Author profile query:", err);
            document.getElementById('author-profile-name').textContent = fallbackName || 'Author Profile';
            document.getElementById('author-profile-affil').textContent = 'Live Google Scholar search link ready.';
        });
        
    loadAuthorWorks(cleanId, 1);
}

function loadAuthorWorks(authorId, page = 1) {
    currentAuthorPage = page;
    const worksList = document.getElementById('author-works-list');
    const loadingDiv = document.getElementById('author-works-loading');
    const prevBtn = document.getElementById('author-prev-btn');
    const nextBtn = document.getElementById('author-next-btn');
    const pageInfo = document.getElementById('author-page-info');
    
    loadingDiv.style.display = 'block';
    worksList.innerHTML = '';
    
    fetch(`/authors/${encodeURIComponent(authorId)}/works?page=${page}&per_page=10&provider=${currentAuthorProvider}`)
        .then(res => res.json())
        .then(data => {
            loadingDiv.style.display = 'none';
            const works = data.results || [];
            const totalCount = data.total_count || works.length;
            currentAuthorTotalPages = Math.ceil(totalCount / 10) || 1;
            
            pageInfo.textContent = `Page ${page} of ${currentAuthorTotalPages}`;
            prevBtn.disabled = page <= 1;
            nextBtn.disabled = page >= currentAuthorTotalPages;
            
            if (works.length === 0) {
                worksList.innerHTML = `<div class="text-muted" style="padding: 1.5rem; text-align: center;">No publications returned from ${currentAuthorProvider === 'google_scholar' ? 'Google Scholar' : 'OpenAlex'}.</div>`;
                return;
            }
            
            works.forEach(w => {
                const item = document.createElement('div');
                item.className = 'work-item';
                
                let doiHtml = '';
                if (w.doi) {
                    doiHtml = `<a href="https://doi.org/${escapeHtml(w.doi)}" target="_blank" class="badge-id badge-id-doi" style="display: inline-flex; font-size: 0.78rem; padding: 0.2rem 0.6rem; margin-top: 0.35rem;">🔗 DOI: ${escapeHtml(w.doi)}</a>`;
                } else if (w.url) {
                    doiHtml = `<a href="${escapeHtml(w.url)}" target="_blank" class="badge-source-link" style="display: inline-flex; font-size: 0.78rem; padding: 0.2rem 0.6rem; margin-top: 0.35rem;">🔗 View Link</a>`;
                }
                
                item.innerHTML = `
                    <div style="font-weight: 600; font-size: 0.98rem; color: var(--text-main);">${escapeHtml(w.title)}</div>
                    <div style="font-size: 0.84rem; color: var(--text-secondary); margin-top: 0.25rem;">
                        <span>📅 ${w.year || '—'}</span>
                        <span style="margin-left: 1rem;">📊 Citations: ${w.citation_count !== null && w.citation_count !== undefined ? w.citation_count.toLocaleString() : '—'}</span>
                        ${w.venue ? `<span style="margin-left: 1rem;">📖 ${escapeHtml(w.venue)}</span>` : ''}
                    </div>
                    <div style="display: flex; gap: 0.5rem; align-items: center; margin-top: 0.4rem; flex-wrap: wrap;">
                        ${doiHtml}
                        <a href="https://scholar.google.com/scholar?q=${encodeURIComponent(w.title)}" target="_blank" class="btn-scholar-ref" style="font-size: 0.75rem; padding: 0.15rem 0.5rem;">🎓 Open Scholar</a>
                    </div>
                `;
                worksList.appendChild(item);
            });
        })
        .catch(err => {
            console.error(err);
            loadingDiv.style.display = 'none';
            worksList.innerHTML = '<div class="text-muted" style="padding: 1rem;">Error loading author publications.</div>';
        });
}

function changeAuthorWorksPage(delta) {
    const newPage = currentAuthorPage + delta;
    if (newPage >= 1 && newPage <= currentAuthorTotalPages) {
        loadAuthorWorks(currentAuthorId, newPage);
    }
}

function closeAuthorProfile() {
    document.getElementById('author-modal').style.display = 'none';
}

// ==========================================
// PROJECT EXPORT LOGIC
// ==========================================
function exportCurrentProject(format = 'json') {
    if (!currentProjectId) {
        showToast('No active project found to export. Please analyze a PDF first.', 'warning');
        return;
    }

    const fmt = format.toLowerCase();
    const exportUrl = `/projects/${encodeURIComponent(currentProjectId)}/export?format=${fmt}`;

    if (fmt === 'json') {
        fetch(exportUrl)
            .then(res => {
                if (!res.ok) throw new Error('Project export failed');
                return res.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${currentProjectId}_bundle.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showToast('JSON bundle downloaded successfully.', 'success');
            })
            .catch(err => showToast(`Export Error: ${err.message}`, 'error'));
    } else if (fmt === 'bibtex') {
        fetch(exportUrl)
            .then(res => {
                if (!res.ok) throw new Error('BibTeX export failed');
                return res.text();
            })
            .then(text => {
                const blob = new Blob([text], { type: 'text/plain' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${currentProjectId}_references.bib`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showToast('Clean BibTeX file downloaded successfully.', 'success');
            })
            .catch(err => showToast(`BibTeX Export Error: ${err.message}`, 'error'));
    } else if (fmt === 'xml') {
        fetch(exportUrl)
            .then(res => {
                if (!res.ok) throw new Error('XML export failed');
                return res.text();
            })
            .then(text => {
                const blob = new Blob([text], { type: 'application/xml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${currentProjectId}_export.xml`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                showToast('XML export downloaded successfully.', 'success');
            })
            .catch(err => showToast(`XML Export Error: ${err.message}`, 'error'));
    }
}

function copyProjectBibtex() {
    if (!currentProjectId) {
        showToast('No active project to copy BibTeX from.', 'warning');
        return;
    }

    fetch(`/projects/${encodeURIComponent(currentProjectId)}/export?format=bibtex`)
        .then(res => {
            if (!res.ok) throw new Error('Failed to retrieve BibTeX');
            return res.text();
        })
        .then(text => {
            navigator.clipboard.writeText(text)
                .then(() => showToast('All references copied as BibTeX!', 'success'))
                .catch(() => showToast('Could not copy to clipboard', 'error'));
        })
        .catch(err => showToast(`Error: ${err.message}`, 'error'));
}
