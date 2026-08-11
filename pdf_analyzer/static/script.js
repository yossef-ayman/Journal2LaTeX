// DOM Elements
const uploadScreen = document.getElementById('upload-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const loadingOverlay = document.getElementById('loading-overlay');
const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');

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

// Drag and drop event listeners
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
    
    if (e.dataTransfer.files.length > 0) {
        handleFile(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (fileInput.files.length > 0) {
        handleFile(fileInput.files[0]);
    }
});

// File processing and upload
function handleFile(file) {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        alert('Please upload a valid PDF file.');
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
            throw new Error('Analysis failed.');
        }
        return response.json();
    })
    .then(data => {
        populateDashboard(data);
        showScreen(dashboardScreen);
    })
    .catch(error => {
        console.error(error);
        alert('An error occurred while analyzing the PDF. Please try again.');
    })
    .finally(() => {
        showLoading(false);
    });
}

// UI Helpers
function showLoading(show) {
    loadingOverlay.style.display = show ? 'flex' : 'none';
}

function showScreen(screen) {
    uploadScreen.classList.remove('active');
    dashboardScreen.classList.remove('active');
    
    // Tiny delay for transitions
    setTimeout(() => {
        uploadScreen.style.display = uploadScreen === screen ? 'block' : 'none';
        dashboardScreen.style.display = dashboardScreen === screen ? 'block' : 'none';
        
        setTimeout(() => {
            screen.classList.add('active');
        }, 50);
    }, 300);
}

function showUploadScreen() {
    showScreen(uploadScreen);
    fileInput.value = '';
}

// Populate Dashboard Content
function populateDashboard(data) {
    articleTitle.textContent = data.title;
    
    let subHeader = data.journal;
    if (data.doi) subHeader += ` • DOI: ${data.doi}`;
    if (data.arxiv_id) subHeader += ` • arXiv: ${data.arxiv_id}`;
    articleJournal.textContent = subHeader;
    
    kpiPages.textContent = data.page_count;
    kpiAuthors.textContent = data.authors.length;
    kpiHeadings.textContent = data.headings.length;
    kpiReferences.textContent = data.references.length;
    
    currentXml = data.xml;
    xmlCode.textContent = data.xml;
    
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
    data.authors.forEach(author => {
        const initials = author.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        
        const chip = document.createElement('div');
        chip.className = 'author-chip';
        chip.innerHTML = `
            <div class="author-avatar">${initials}</div>
            <div class="author-name">${author}</div>
        `;
        chip.onclick = () => analyzeElement('author', { text: author });
        authorsList.appendChild(chip);
    });
    
    // Affiliations
    const affilContainer = document.getElementById('affiliations-list');
    if (data.affiliations && data.affiliations.length > 0) {
        affilContainer.innerHTML = '<strong>Affiliations:</strong><br>' + data.affiliations.map(a => escapeHtml(a)).join('<br>');
    } else {
        affilContainer.innerHTML = '';
    }
    
    // Populate Headings Outline
    headingsOutline.innerHTML = '';
    if (data.headings.length === 0) {
        headingsOutline.innerHTML = '<div class="text-muted" style="padding: 1rem;">No headings identified in the document structure.</div>';
    } else {
        data.headings.forEach(heading => {
            const item = document.createElement('div');
            item.className = `heading-item level-${heading.level}`;
            item.innerHTML = `
                ${escapeHtml(heading.text)}
                <span class="heading-page">P. ${heading.page}</span>
            `;
            item.onclick = () => analyzeElement('heading', { text: heading.text, level: heading.level, page: heading.page });
            headingsOutline.appendChild(item);
        });
    }

    // Populate References List with Google Search buttons
    referencesList.innerHTML = '';
    if (data.references.length === 0) {
        referencesList.innerHTML = '<div class="text-muted" style="padding: 1rem;">No references identified in the bibliography section.</div>';
    } else {
        data.references.forEach(ref => {
            const item = document.createElement('div');
            item.className = 'ref-item';
            
            const cleanQuery = cleanRefQuery(ref.text);
            const encodedQuery = encodeURIComponent(cleanQuery);
            const googleUrl = `https://www.google.com/search?q=${encodedQuery}`;
            const scholarUrl = `https://scholar.google.com/scholar?q=${encodedQuery}`;
            
            item.innerHTML = `
                <div class="ref-header">
                    <span><strong>[${ref.id}]</strong> ${escapeHtml(ref.text)}</span>
                </div>
                <div class="ref-search-btns">
                    <a href="${googleUrl}" target="_blank" class="btn-search-ref" onclick="event.stopPropagation();">🔍 Search Google</a>
                    <a href="${scholarUrl}" target="_blank" class="btn-scholar-ref" onclick="event.stopPropagation();">🎓 Google Scholar</a>
                </div>
            `;
            item.onclick = () => {
                analyzeElement('reference', { text: ref.text, cleanQuery, id: ref.id, googleUrl, scholarUrl });
            };
            referencesList.appendChild(item);
        });
    }
}

// Clean reference text to isolate title for Google Search
function cleanRefQuery(refText) {
    if (!refText) return '';
    let text = refText.trim();
    
    // Remove leading brackets or numbers [1], 1., (1)
    text = text.replace(/^(?:\[\d+\]|\(\d+\)|\d+\.)\s*/, '');
    
    // Check if title is enclosed in quotes: "Title of Paper" or “Title of Paper”
    const quoteMatch = text.match(/["“]([^"”]+)["”]/);
    if (quoteMatch && quoteMatch[1].length > 8) {
        return quoteMatch[1].trim();
    }
    
    // Strip Author + Year pattern at start: "Rikabi, A. (2018)." or "Smith et al. (2020)."
    const yearMatch = text.match(/\(\d{4}\)\.\s*/);
    if (yearMatch && yearMatch.index !== undefined) {
        const titlePart = text.substring(yearMatch.index + yearMatch[0].length).trim();
        if (titlePart.length > 5) {
            return titlePart;
        }
    }
    
    return text.trim() || refText.trim();
}

// Tab Switching
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
    } else if (type === 'reference') {
        typeTitle.textContent = `📚 Reference [${data.id}] Analysis`;
        typeVal.textContent = 'Bibliography Reference Citation';
        pageRow.style.display = 'none';
        
        const searchTitle = data.cleanQuery || cleanRefQuery(data.text);
        const q = encodeURIComponent(searchTitle);
        const gUrl = `https://www.google.com/search?q=${q}`;
        const sUrl = `https://scholar.google.com/scholar?q=${q}`;
        
        let notes = `<strong>Cleaned Search Title:</strong><br><em style="color: var(--secondary-color);">${escapeHtml(searchTitle)}</em><br><br>
        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
            <a href="${gUrl}" target="_blank" class="btn-search-ref">🔍 Search Title on Google</a>
            <a href="${sUrl}" target="_blank" class="btn-scholar-ref">🎓 Search Google Scholar</a>
        </div>`;
        notesVal.innerHTML = notes;
    }
}

// Clipboard copy helper
function copyXml() {
    navigator.clipboard.writeText(currentXml)
        .then(() => {
            alert('XML content copied to clipboard!');
        })
        .catch(err => {
            console.error('Could not copy text: ', err);
        });
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
}

// HTML escape helper
function escapeHtml(str) {
    return str.replace(/&/g, "&amp;")
              .replace(/</g, "&lt;")
              .replace(/>/g, "&gt;")
              .replace(/"/g, "&quot;")
              .replace(/'/g, "&#039;");
}
