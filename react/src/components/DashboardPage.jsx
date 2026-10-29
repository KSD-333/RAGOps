import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, 
  Coins, 
  RotateCw, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  Server, 
  CreditCard, 
  Zap, 
  Layers, 
  TrendingUp,
  Search,
  DollarSign,
  Users,
  MessageSquare,
  ShieldAlert,
  HelpCircle,
  Download,
  Filter,
  ChevronDown,
  ChevronUp,
  Database,
  ExternalLink,
  Award,
  Sparkles,
  UserCheck,
  User,
  ArrowRight,
  Upload,
  Globe,
  Building,
  FileText,
  Plus,
  Trash2,
  Edit3,
  Save,
  RefreshCw,
  Briefcase,
  MapPin,
  Check,
  XCircle,
  Tag,
  Eye,
  GitMerge,
  Copy,
  ChevronRight,
  ArrowLeft,
  Bot,
  Maximize2,
  Minimize2
} from 'lucide-react';
import { marked } from 'marked';

export default function DashboardPage({ onRerunQuery, apiBaseUrl = '', currentUser, onOpenAuthModal, onChunkClick }) {
  // Navigation tabs within Dashboard (support deep-linking to company knowledge hub)
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window !== 'undefined') {
      const hash = window.location.hash.toLowerCase();
      if (hash.includes('company') || hash.includes('catalog') || hash.includes('location')) return 'catalog';
    }
    return 'overview';
  });

  // Data states
  const [feedbackData, setFeedbackData] = useState(null);
  const [adminAnalytics, setAdminAnalytics] = useState(null);
  const [userList, setUserList] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userChatHistory, setUserChatHistory] = useState([]);
  const [recentLogs, setRecentLogs] = useState([]);
  const [frequentQueries, setFrequentQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [expandedMessageId, setExpandedMessageId] = useState(null);
  const [riskFilter, setRiskFilter] = useState(false);

  // Tab 2: User Directory & Side-by-Side Chat Audit States
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [chatSearchQuery, setChatSearchQuery] = useState('');
  const [chatRiskFilterOnly, setChatRiskFilterOnly] = useState(false);
  const [copiedAuditText, setCopiedAuditText] = useState(null);
  const [mobileChatView, setMobileChatView] = useState('list'); // 'list' | 'chat'

  // Tab 3: Trace Viewer & Retrieval Inspector States
  const [expandedTraceIds, setExpandedTraceIds] = useState({});
  const [traceSearchQuery, setTraceSearchQuery] = useState('');
  const [traceLatencyFilter, setTraceLatencyFilter] = useState('all'); // 'all' | 'risk' | 'slow'
  const [copiedTraceText, setCopiedTraceText] = useState(null);

  // Document Catalog & Semantic Cache States
  const [catalogData, setCatalogData] = useState(null);
  const [cacheStats, setCacheStats] = useState(null);
  const [catalogFilter, setCatalogFilter] = useState('all'); // 'all' | 'policy' | 'code' | 'programme' | 'governance' | 'manual'
  const [catalogSearch, setCatalogSearch] = useState('');
  const [isClearingCache, setIsClearingCache] = useState(false);

  // Dynamic Company Profile & Web Intelligence States
  const [companyProfile, setCompanyProfile] = useState(null);
  const [isScrapingCompany, setIsScrapingCompany] = useState(false);
  const [isExtractingCompany, setIsExtractingCompany] = useState(false);
  const [scrapeResultMsg, setScrapeResultMsg] = useState('');
  const [newCompanyUrl, setNewCompanyUrl] = useState('');
  const [companyUrlInput, setCompanyUrlInput] = useState('');
  const [isEditingCompany, setIsEditingCompany] = useState(false);
  const [isReviewMode, setIsReviewMode] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [isApprovingProfile, setIsApprovingProfile] = useState(false);
  const [isReindexingEmbeddings, setIsReindexingEmbeddings] = useState(false);

  // Source-Backed Fact Validation & Outbox States
  const [companyHubSubTab, setCompanyHubSubTab] = useState('candidates'); // 'candidates' | 'approved' | 'outbox' | 'edit_profile'
  const [factCandidates, setFactCandidates] = useState([]);
  const [approvedFacts, setApprovedFacts] = useState([]);
  const [outboxEvents, setOutboxEvents] = useState([]);
  const [companySources, setCompanySources] = useState([]);
  const [candidateSectionFilter, setCandidateSectionFilter] = useState('all');
  const [editingCandidateId, setEditingCandidateId] = useState(null);
  const [editingCandidateValue, setEditingCandidateValue] = useState('');
  const [isProcessingOutbox, setIsProcessingOutbox] = useState(false);
  const [isSeedingKnowledge, setIsSeedingKnowledge] = useState(false);

  // Universal Multi-Company & Autonomous Research Tool States
  const [trackedCompanies, setTrackedCompanies] = useState([]);
  const [selectedOrgId, setSelectedOrgId] = useState('default_org');
  const [fillGapsWithSearch, setFillGapsWithSearch] = useState(true);
  const [reconcilingCandidate, setReconcilingCandidate] = useState(null);
  const [reconciledValueInput, setReconciledValueInput] = useState('');
  const [reconciledReasonInput, setReconciledReasonInput] = useState('');
  const [showSearchToolDrawer, setShowSearchToolDrawer] = useState(false);
  const [searchToolFactType, setSearchToolFactType] = useState('leadership');
  const [searchToolResults, setSearchToolResults] = useState([]);
  const [isSearchingGap, setIsSearchingGap] = useState(false);

  const [newLocationInput, setNewLocationInput] = useState({
    city: '',
    state: '',
    country: 'India',
    type: 'Manufacturing Plant',
    address: '',
  });
  const [newClientInput, setNewClientInput] = useState('');
  const [newHubInput, setNewHubInput] = useState('');
  const [newProductInput, setNewProductInput] = useState('');
  const [companyForm, setCompanyForm] = useState({
    company_name: '',
    group_name: '',
    industry: '',
    description: '',
    ceo: '',
    founded_year: '',
    employee_details: '',
    clients: [],
    hubs: [],
    products: [],
    locations: [],
    domains_urls: [],
  });

  // Document Upload States (with Title input & Filename fallback)
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [docUploadTitle, setDocUploadTitle] = useState('');
  const [selectedUploadFile, setSelectedUploadFile] = useState(null);
  const fileInputRef = useRef(null);

  // Storage Reconciliation & Embedding States
  const [isSyncingDisk, setIsSyncingDisk] = useState(false);
  const [isEmbeddingAll, setIsEmbeddingAll] = useState(false);
  const [embeddingSources, setEmbeddingSources] = useState({});

  // Billing Configuration (stored in localStorage)
  const [planTokens, setPlanTokens] = useState(() => {
    return Number(localStorage.getItem('ragops_plan_tokens')) || 5000000;
  });
  const [planPrice, setPlanPrice] = useState(() => {
    return Number(localStorage.getItem('ragops_plan_price')) || 2000;
  });
  const [currencySymbol, setCurrencySymbol] = useState(() => {
    return localStorage.getItem('ragops_currency') || '₹';
  });

  const fetchAllData = async () => {
    setLoading(true);
    try {
      // 1. Fetch Feedback Dashboard Summary
      const resFeedback = await fetch(`${apiBaseUrl}/api/v1/feedback/dashboard`);
      if (resFeedback.ok) {
        setFeedbackData(await resFeedback.json());
      }

      // 2. Fetch Admin Analytics
      const resAnalytics = await fetch(`${apiBaseUrl}/api/v1/admin/analytics`);
      if (resAnalytics.ok) {
        const json = await resAnalytics.json();
        setAdminAnalytics(json);
        if (json.frequent_queries) setFrequentQueries(json.frequent_queries);
      }

      // 3. Fetch User List with Stats
      const resUsers = await fetch(`${apiBaseUrl}/api/v1/admin/users`);
      if (resUsers.ok) {
        const json = await resUsers.json();
        setUserList(json.users || []);
        if (json.users?.length > 0 && !selectedUser) {
          // Default select first active user
          setSelectedUser(json.users[0].username);
        }
      }

      // 4. Fetch All Query Logs
      const resLogs = await fetch(`${apiBaseUrl}/api/v1/admin/logs?limit=40`);
      if (resLogs.ok) {
        const json = await resLogs.json();
        setRecentLogs(json.logs || []);
      }

      // 5. Fetch Document Catalog & Auto-Classifications
      const resCatalog = await fetch(`${apiBaseUrl}/api/v1/catalog`);
      if (resCatalog.ok) {
        setCatalogData(await resCatalog.json());
      }

      // 6. Fetch Semantic Cache Performance Metrics
      const resCache = await fetch(`${apiBaseUrl}/api/v1/cache/stats`);
      if (resCache.ok) {
        setCacheStats(await resCache.json());
      }

      // 7. Fetch Dynamic Company Profile
      const resCompany = await fetch(`${apiBaseUrl}/api/v1/company/profile`);
      if (resCompany.ok) {
        const compJson = await resCompany.json();
        const prof = compJson.profile;
        setCompanyProfile(prof || null);
        if (prof) {
          const meta = prof.metadata_json || {};
          const clientsList = Array.isArray(meta.clients) ? meta.clients : (typeof meta.clients === 'string' && meta.clients ? meta.clients.split(',').map((s) => s.trim()).filter(Boolean) : []);
          const hubsList = Array.isArray(meta.hubs) ? meta.hubs : (typeof meta.hubs === 'string' && meta.hubs ? meta.hubs.split(',').map((s) => s.trim()).filter(Boolean) : []);
          const prodsList = Array.isArray(prof.products) ? prof.products : [];
          const locsList = Array.isArray(prof.locations) ? prof.locations : [];
          const urlsList = Array.isArray(prof.domains_urls) ? prof.domains_urls : [];
          setCompanyForm({
            company_name: prof.company_name || '',
            group_name: prof.group_name || '',
            industry: prof.industry || '',
            description: prof.description || '',
            ceo: prof.ceo || '',
            founded_year: meta.founded_year || prof.founded_year || '',
            employee_details: prof.employee_details || '',
            clients: clientsList,
            hubs: hubsList,
            products: prodsList,
            locations: locsList,
            domains_urls: urlsList,
          });
          if (urlsList.length > 0) {
            setCompanyUrlInput(urlsList[0]);
          }
        }
      }

      // 8. Fetch Fact Candidates for Review
      try {
        const resCand = await fetch(`${apiBaseUrl}/api/v1/company/candidates`);
        if (resCand.ok) {
          const cJson = await resCand.json();
          setFactCandidates(cJson.candidates || []);
        }
      } catch (eCand) {
        console.warn('Failed to load fact candidates:', eCand);
      }

      // 9. Fetch Approved Structured Facts
      try {
        const resFacts = await fetch(`${apiBaseUrl}/api/v1/company/knowledge`);
        if (resFacts.ok) {
          const fJson = await resFacts.json();
          setApprovedFacts(fJson.facts || []);
        }
      } catch (eFacts) {
        console.warn('Failed to load approved facts:', eFacts);
      }

      // 10. Fetch Publication Outbox Events
      try {
        const resOutbox = await fetch(`${apiBaseUrl}/api/v1/company/outbox`);
        if (resOutbox.ok) {
          const oJson = await resOutbox.json();
          setOutboxEvents(oJson.outbox_events || []);
        }
      } catch (eOutbox) {
        console.warn('Failed to load outbox events:', eOutbox);
      }

      // 11. Fetch Tracked Companies
      await fetchTrackedCompanies();
    } catch (err) {
      console.error('Failed to fetch dashboard telemetry:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTrackedCompanies = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/universal/companies`);
      if (res.ok) {
        const data = await res.json();
        setTrackedCompanies(data.companies || []);
      }
    } catch (err) {
      console.warn('Failed to load tracked companies:', err);
    }
  };

  const fetchFactCandidates = async (orgId = null) => {
    try {
      const targetOrg = orgId || selectedOrgId;
      const res = await fetch(`${apiBaseUrl}/api/v1/company/candidates?organization_id=${targetOrg}`);
      if (res.ok) {
        const data = await res.json();
        setFactCandidates(data.candidates || []);
      }
    } catch (err) {
      console.error('Failed to fetch candidates:', err);
    }
  };

  const fetchApprovedFacts = async (orgId = null) => {
    try {
      const targetOrg = orgId || selectedOrgId;
      const res = await fetch(`${apiBaseUrl}/api/v1/company/knowledge?organization_id=${targetOrg}`);
      if (res.ok) {
        const data = await res.json();
        setApprovedFacts(data.facts || []);
      }
    } catch (err) {
      console.error('Failed to fetch approved facts:', err);
    }
  };

  const fetchOutboxEvents = async (orgId = null) => {
    try {
      const targetOrg = orgId || selectedOrgId;
      const res = await fetch(`${apiBaseUrl}/api/v1/company/outbox?organization_id=${targetOrg}`);
      if (res.ok) {
        const data = await res.json();
        setOutboxEvents(data.outbox_events || []);
      }
    } catch (err) {
      console.error('Failed to fetch outbox events:', err);
    }
  };

  const handleExecuteQuickGapSearch = async () => {
    const targetName = companyForm.company_name || 'Enterprise';
    setIsSearchingGap(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/universal/search-gap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: targetName,
          fact_type: searchToolFactType,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSearchToolResults(data.results || []);
      }
    } catch (err) {
      console.error('Gap search failed:', err);
    } finally {
      setIsSearchingGap(false);
    }
  };

  const handleReviewCandidate = async (candidateId, decision, submittedValue = null, reason = null) => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/candidates/${candidateId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          reviewer_id: currentUser?.username || 'admin',
          submitted_value: submittedValue,
          reason,
        }),
      });
      if (res.ok) {
        await Promise.all([
          fetchFactCandidates(selectedOrgId),
          fetchApprovedFacts(selectedOrgId),
          fetchOutboxEvents(selectedOrgId),
          fetchTrackedCompanies(),
        ]);
        setScrapeResultMsg(`Fact candidate status updated to '${decision}' with transactional outbox queue.`);
        setTimeout(() => setScrapeResultMsg(''), 6000);
      }
    } catch (err) {
      console.error('Failed to review candidate:', err);
    }
  };

  const handleSaveCandidateEdit = async (candidateId) => {
    try {
      let parsedValue = editingCandidateValue;
      try {
        parsedValue = JSON.parse(editingCandidateValue);
      } catch (_) {
        // Keep as string
      }
      const res = await fetch(`${apiBaseUrl}/api/v1/company/candidates/${candidateId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposed_value: parsedValue }),
      });
      if (res.ok) {
        setEditingCandidateId(null);
        setEditingCandidateValue('');
        await fetchFactCandidates();
      }
    } catch (err) {
      console.error('Failed to edit candidate value:', err);
    }
  };

  const handleProcessOutbox = async () => {
    setIsProcessingOutbox(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/publish-outbox/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 50 }),
      });
      if (res.ok) {
        const data = await res.json();
        setScrapeResultMsg(`⚡ Published ${data.result?.processed || 0} facts to ChromaDB vector store safely!`);
        await Promise.all([fetchOutboxEvents(), fetchApprovedFacts()]);
        setTimeout(() => setScrapeResultMsg(''), 8000);
      }
    } catch (err) {
      console.error('Failed to process publication outbox:', err);
    } finally {
      setIsProcessingOutbox(false);
    }
  };

  const [isClearingCompany, setIsClearingCompany] = useState(false);

  const handleClearCompanyData = async (clearAll = true) => {
    if (!window.confirm(clearAll 
      ? 'Are you sure you want to completely clear ALL previous company info, candidates, facts, and profile? This gives you a clean slate for any new enterprise.'
      : `Are you sure you want to clear company data for ${selectedOrgId}?`
    )) {
      return;
    }
    setIsClearingCompany(true);
    setScrapeResultMsg('🧹 Clearing corporate facts, candidates, review queue, and profile...');
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/clear`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          organization_id: clearAll ? null : selectedOrgId,
          clear_all: clearAll,
        }),
      });
      if (res.ok) {
        setCompanyForm({
          company_name: '',
          group_name: '',
          industry: '',
          description: '',
          ceo: '',
          founded_year: '',
          employee_details: '',
          clients: [],
          hubs: [],
          products: [],
          locations: [],
          domains_urls: [],
        });
        setCompanyUrlInput('');
        setCompanyProfile(null);
        setFactCandidates([]);
        setApprovedFacts([]);
        setOutboxEvents([]);
        setSelectedOrgId('default_org');
        setTrackedCompanies([]);
        await fetchTrackedCompanies();
        setScrapeResultMsg('✨ Clean slate: All previous company data wiped cleanly! Ready for any enterprise URL.');
        setTimeout(() => setScrapeResultMsg(''), 6000);
      } else {
        const errJson = await res.json().catch(() => ({}));
        setScrapeResultMsg(`⚠️ Failed to clear company data: ${errJson.detail || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Failed to clear company data:', err);
      setScrapeResultMsg(`❌ Clear error: ${err.message}`);
    } finally {
      setIsClearingCompany(false);
    }
  };

  const handleClearCache = async () => {
    setIsClearingCache(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/cache`, { method: 'DELETE' });
      if (res.ok) {
        const resCache = await fetch(`${apiBaseUrl}/api/v1/cache/stats`);
        if (resCache.ok) setCacheStats(await resCache.json());
      }
    } catch (err) {
      console.error('Failed to clear cache:', err);
    } finally {
      setIsClearingCache(false);
    }
  };

  const handleAddCompanyUrl = async (e) => {
    if (e) e.preventDefault();
    const url = newCompanyUrl.trim();
    if (!url) return;
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/urls`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        const data = await res.json();
        setCompanyProfile((prev) => ({ ...prev, domains_urls: data.domains_urls }));
        setNewCompanyUrl('');
      }
    } catch (err) {
      console.error('Failed to add company URL:', err);
    }
  };

  const handleRemoveCompanyUrl = async (url) => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/urls`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });
      if (res.ok) {
        const data = await res.json();
        setCompanyProfile((prev) => ({ ...prev, domains_urls: data.domains_urls }));
      }
    } catch (err) {
      console.error('Failed to remove URL:', err);
    }
  };

  const handleExtractCompanyFromUrl = async (urlOverride = null) => {
    const target = (urlOverride || companyUrlInput || newCompanyUrl).trim();
    if (!target) {
      alert('Please enter any company website URL (e.g. https://example.com)');
      return;
    }
    setIsExtractingCompany(true);
    setIsScrapingCompany(true);
    setScrapeResultMsg('🌐 Universal Autonomous AI: Crawling multi-page site, discovering subpages, & researching missing facts with AI Search Tool...');
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/universal/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: target,
          company_name: companyForm.company_name || null,
          organization_id: selectedOrgId !== 'default_org' ? selectedOrgId : null,
          max_pages: 6,
          fill_gaps_with_search: fillGapsWithSearch,
        }),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        const analysis = data.analysis;
        setSelectedOrgId(analysis.organization_id);
        await Promise.all([
          fetchFactCandidates(analysis.organization_id),
          fetchApprovedFacts(analysis.organization_id),
          fetchOutboxEvents(analysis.organization_id),
          fetchTrackedCompanies(),
        ]);
        setCompanyHubSubTab('candidates');
        setScrapeResultMsg(`✅ Universal AI Extraction Complete for ${analysis.company_name}: Crawled ${analysis.pages_crawled} pages, executed ${analysis.search_queries_executed} AI searches, and staged ${analysis.candidates_count} candidate facts in PostgreSQL!`);
      } else {
        setScrapeResultMsg(`⚠️ ${data.detail || data.message || 'Analysis completed with warnings.'}`);
      }
      setTimeout(() => setScrapeResultMsg(''), 10000);
    } catch (err) {
      setScrapeResultMsg(`❌ Crawl error: ${err.message}`);
    } finally {
      setIsExtractingCompany(false);
      setIsScrapingCompany(false);
    }
  };

  const handleSaveAndEmbedCompanyProfile = async (e) => {
    if (e) e.preventDefault();
    setIsApprovingProfile(true);
    setScrapeResultMsg('⚡ Storing verified corporate facts into PostgreSQL & ChromaDB vector store...');
    try {
      const payload = {
        company_name: companyForm.company_name || 'Enterprise',
        group_name: companyForm.group_name || '',
        industry: companyForm.industry || '',
        description: companyForm.description || '',
        ceo: companyForm.ceo || '',
        employee_details: companyForm.employee_details || '',
        products: companyForm.products || [],
        locations: companyForm.locations || [],
        directors: previewData?.directors || companyProfile?.directors || [],
        domains_urls: companyForm.domains_urls?.length ? companyForm.domains_urls : [companyUrlInput],
        metadata_json: {
          ...(companyProfile?.metadata_json || {}),
          ...(previewData?.metadata_json || {}),
          clients: companyForm.clients || [],
          hubs: companyForm.hubs || [],
          founded_year: companyForm.founded_year || '',
        },
      };

      const res = await fetch(`${apiBaseUrl}/api/v1/company/approve-and-embed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        setCompanyProfile(data.profile);
        setIsReviewMode(false);
        setIsEditingCompany(false);
        setIsPreviewModalOpen(false);
        setScrapeResultMsg(`✅ Verified company facts saved to PostgreSQL & ${data.chunks_embedded || 5} chunks embedded into Vector Store!`);
      } else {
        alert(data.detail || data.message || 'Failed to save and embed company profile.');
      }
      setTimeout(() => setScrapeResultMsg(''), 10000);
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    } finally {
      setIsApprovingProfile(false);
    }
  };

  const handleAddLocationItem = () => {
    if (!newLocationInput.city.trim()) {
      alert('Please enter at least a City for the location.');
      return;
    }
    const currentLocs = companyForm.locations || [];
    setCompanyForm({
      ...companyForm,
      locations: [...currentLocs, { ...newLocationInput }],
    });
    setNewLocationInput({ city: '', state: '', country: 'India', type: 'Manufacturing Plant', address: '' });
  };

  const handleDeleteLocationItem = (index) => {
    const updated = (companyForm.locations || []).filter((_, i) => i !== index);
    setCompanyForm({ ...companyForm, locations: updated });
  };

  const handleAddClientItem = () => {
    if (!newClientInput.trim()) return;
    const current = companyForm.clients || [];
    if (!current.includes(newClientInput.trim())) {
      setCompanyForm({ ...companyForm, clients: [...current, newClientInput.trim()] });
    }
    setNewClientInput('');
  };

  const handleDeleteClientItem = (index) => {
    const updated = (companyForm.clients || []).filter((_, i) => i !== index);
    setCompanyForm({ ...companyForm, clients: updated });
  };

  const handleAddProductItem = () => {
    if (!newProductInput.trim()) return;
    const current = companyForm.products || [];
    if (!current.includes(newProductInput.trim())) {
      setCompanyForm({ ...companyForm, products: [...current, newProductInput.trim()] });
    }
    setNewProductInput('');
  };

  const handleDeleteProductItem = (index) => {
    const updated = (companyForm.products || []).filter((_, i) => i !== index);
    setCompanyForm({ ...companyForm, products: updated });
  };

  const handleAddHubItem = () => {
    if (!newHubInput.trim()) return;
    const current = companyForm.hubs || [];
    if (!current.includes(newHubInput.trim())) {
      setCompanyForm({ ...companyForm, hubs: [...current, newHubInput.trim()] });
    }
    setNewHubInput('');
  };

  const handleDeleteHubItem = (index) => {
    const updated = (companyForm.hubs || []).filter((_, i) => i !== index);
    setCompanyForm({ ...companyForm, hubs: updated });
  };

  const handleReindexEmbeddings = async () => {
    setIsReindexingEmbeddings(true);
    setScrapeResultMsg('⚡ Re-embedding corporate profile into ChromaDB vector store...');
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/reindex-embeddings`, {
        method: 'POST',
      });
      const data = await res.json();
      if (res.ok) {
        setScrapeResultMsg(`✅ ${data.message}`);
      } else {
        setScrapeResultMsg(`⚠️ Failed to re-index: ${data.detail || 'Unknown error'}`);
      }
      setTimeout(() => setScrapeResultMsg(''), 8000);
    } catch (err) {
      setScrapeResultMsg(`❌ Embedding error: ${err.message}`);
    } finally {
      setIsReindexingEmbeddings(false);
    }
  };

  const handleUploadDocument = async (fileToUpload = null) => {
    const file = fileToUpload || selectedUploadFile;
    if (!file) return;
    setIsUploadingDoc(true);
    setUploadFeedback(null);
    const formData = new FormData();
    formData.append('file', file);
    // Use user-provided document title; if not given, backend/frontend defaults to PDF file name
    const effectiveTitle = docUploadTitle.trim() || file.name;
    formData.append('title', effectiveTitle);

    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/catalog/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');
      setUploadFeedback({
        type: 'success',
        message: `Successfully ingested "${data.filename}" (Title: "${data.title}")! Auto-classified as: ${data.doc_type?.toUpperCase()} (${data.category}) • ${data.chunks_indexed} chunks indexed into ChromaDB.`,
      });
      setSelectedUploadFile(null);
      setDocUploadTitle('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      // Refresh catalog data
      const resCatalog = await fetch(`${apiBaseUrl}/api/v1/catalog`);
      if (resCatalog.ok) setCatalogData(await resCatalog.json());
    } catch (err) {
      setUploadFeedback({
        type: 'error',
        message: `Upload failed: ${err.message}`,
      });
    } finally {
      setIsUploadingDoc(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const handleSyncWithDisk = async () => {
    setIsSyncingDisk(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/catalog/sync`, { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        setCatalogData({
          summary: json.summary,
          documents: json.documents,
        });
        setUploadFeedback({
          type: 'success',
          message: `Storage reconciled: ${json.summary?.total_documents ?? 0} files detected (${json.summary?.embedded_documents ?? 0} embedded, ${json.summary?.pending_documents ?? 0} pending).`,
        });
      } else {
        throw new Error(`Sync failed with status ${res.status}`);
      }
    } catch (err) {
      console.error('Failed to sync catalog with disk:', err);
      setUploadFeedback({
        type: 'error',
        message: `Failed to sync with disk: ${err.message}`,
      });
    } finally {
      setIsSyncingDisk(false);
    }
  };

  const handleEmbedSingle = async (source) => {
    setEmbeddingSources((prev) => ({ ...prev, [source]: true }));
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/catalog/embed/${encodeURIComponent(source)}`, {
        method: 'POST',
      });
      if (res.ok) {
        const result = await res.json();
        const resCatalog = await fetch(`${apiBaseUrl}/api/v1/catalog`);
        if (resCatalog.ok) setCatalogData(await resCatalog.json());
        setUploadFeedback({
          type: 'success',
          message: `Successfully indexed "${source}" (${result.chunks_indexed} vector chunks created in ChromaDB).`,
        });
      } else {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Embedding failed with status ${res.status}`);
      }
    } catch (err) {
      console.error(`Failed to embed ${source}:`, err);
      setUploadFeedback({
        type: 'error',
        message: `Failed to embed "${source}": ${err.message}`,
      });
    } finally {
      setEmbeddingSources((prev) => ({ ...prev, [source]: false }));
    }
  };

  const handleEmbedAllPending = async () => {
    setIsEmbeddingAll(true);
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/catalog/embed-all`, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        const resCatalog = await fetch(`${apiBaseUrl}/api/v1/catalog`);
        if (resCatalog.ok) setCatalogData(await resCatalog.json());
        setUploadFeedback({
          type: 'success',
          message: `Batch indexing complete: ${result.total_embedded_files} documents embedded (${result.total_chunks_indexed} total vector chunks in ChromaDB).`,
        });
      } else {
        throw new Error(`Batch embedding failed with status ${res.status}`);
      }
    } catch (err) {
      console.error('Failed to embed all pending documents:', err);
      setUploadFeedback({
        type: 'error',
        message: `Batch embedding failed: ${err.message}`,
      });
    } finally {
      setIsEmbeddingAll(false);
    }
  };

  const handleDeleteDocument = async (source) => {
    if (!confirm(`Are you sure you want to permanently delete "${source}" from data/raw disk storage, remove its vector embeddings from ChromaDB, and delete its database record?`)) return;
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/catalog/${encodeURIComponent(source)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        const resCatalog = await fetch(`${apiBaseUrl}/api/v1/catalog`);
        if (resCatalog.ok) setCatalogData(await resCatalog.json());
        setUploadFeedback({
          type: 'success',
          message: `Deleted "${source}", purged physical file from disk, and removed its vector chunks from ChromaDB.`,
        });
      } else {
        throw new Error(`Delete failed with status ${res.status}`);
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
      setUploadFeedback({
        type: 'error',
        message: `Failed to delete document: ${err.message}`,
      });
    }
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  // Fetch individual user chat history whenever selectedUser changes
  useEffect(() => {
    if (!selectedUser) return;
    const fetchUserHistory = async () => {
      setHistoryLoading(true);
      try {
        const res = await fetch(`${apiBaseUrl}/api/v1/admin/users/${selectedUser}/history?limit=50`);
        if (res.ok) {
          const json = await res.json();
          const history = json.history || [];
          setUserChatHistory(history);
          if (history.length > 0) {
            setSelectedSessionId(history[0].session_id || 'default_session');
          } else {
            setSelectedSessionId(null);
          }
          setMobileChatView('list');
        }
      } catch (err) {
        console.error('Failed to load user chat history:', err);
      } finally {
        setHistoryLoading(false);
      }
    };
    fetchUserHistory();
  }, [selectedUser]);

  const handleCopyAuditText = (text, id) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedAuditText(id);
    setTimeout(() => setCopiedAuditText(null), 2000);
  };

  const handleCopyTraceText = (text, id) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopiedTraceText(id);
    setTimeout(() => setCopiedTraceText(null), 2000);
  };

  const toggleTraceExpand = (traceId) => {
    setExpandedTraceIds((prev) => ({
      ...prev,
      [traceId]: !prev[traceId],
    }));
  };

  const handleExpandAllTraces = (tracesList) => {
    const nextMap = {};
    (tracesList || []).forEach((t) => {
      const k = t.id || t.trace_id;
      if (k) nextMap[k] = true;
    });
    setExpandedTraceIds(nextMap);
  };

  const handleCollapseAllTraces = () => {
    setExpandedTraceIds({});
  };

  const handleExportTrainingData = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/admin/training-export?limit=500`);
      if (res.ok) {
        const data = await res.json();
        const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
          JSON.stringify(data.samples, null, 2)
        )}`;
        const downloadAnchor = document.createElement('a');
        downloadAnchor.setAttribute('href', jsonString);
        downloadAnchor.setAttribute('download', `ragops_training_dataset_${Date.now()}.json`);
        document.body.appendChild(downloadAnchor);
        downloadAnchor.click();
        downloadAnchor.remove();
      }
    } catch (err) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleSaveBudget = (e) => {
    e.preventDefault();
    localStorage.setItem('ragops_plan_tokens', planTokens);
    localStorage.setItem('ragops_plan_price', planPrice);
    localStorage.setItem('ragops_currency', currencySymbol);
    alert('Billing plan settings saved successfully!');
  };

  // Calculations
  const totalTokens = (adminAnalytics?.total_tokens ?? feedbackData?.total_tokens) || 0;
  const totalQueries = (adminAnalytics?.total_queries ?? feedbackData?.total_queries) || 0;
  const positiveRate = feedbackData?.positive_rate !== undefined ? Math.round(feedbackData.positive_rate * 100) : 100;
  const latencyStats = feedbackData?.latency_stats || {};
  const p95Latency = Math.round(latencyStats.p95 || 1412);
  const p50Latency = Math.round(latencyStats.p50 || 1350);
  const docsIndexed = adminAnalytics?.documents_indexed || feedbackData?.documents_indexed || 95;
  const activeDbEngine = adminAnalytics?.database_engine || 'postgresql';

  // Cost and budget metrics
  const tokenUsagePct = planTokens > 0 ? ((totalTokens / planTokens) * 100).toFixed(2) : '0.00';
  const billedAmount = planTokens > 0 ? ((totalTokens / planTokens) * planPrice).toFixed(2) : '0.00';
  const remainingTokens = Math.max(planTokens - totalTokens, 0);
  const costPerQuery = totalQueries > 0 ? (Number(billedAmount) / totalQueries).toFixed(3) : '0.000';

  const policyRiskCount = adminAnalytics?.policy_risk_count || 0;
  const churnRiskCount = adminAnalytics?.churn_risk_count || 0;

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      
      {/* Top Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl sm:text-3xl font-bold text-white font-['Outfit'] flex items-center gap-2.5">
              <Activity className="w-7 h-7 text-indigo-400" />
              <span>RAGOps Enterprise Observability &amp; User Intelligence</span>
            </h1>
            <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold flex items-center gap-1.5 border ${
              activeDbEngine === 'postgresql'
                ? 'bg-blue-500/15 text-blue-300 border-blue-500/30'
                : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
            }`}>
              <Database className="w-3 h-3" />
              <span>DB: {activeDbEngine.toUpperCase()}</span>
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Real-time LLMOps telemetry: token spend tracking, user session audits, chunk provenance, and ML training dataset export.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchAllData}
            disabled={loading}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/10 text-xs font-semibold transition-all cursor-pointer"
          >
            <RotateCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={handleExportTrainingData}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl bg-gradient-to-r from-emerald-600/30 to-cyan-600/30 hover:from-emerald-600/40 hover:to-cyan-600/40 text-emerald-300 border border-emerald-500/30 text-xs font-semibold transition-all cursor-pointer shadow-sm"
            title="Download positive grounded Q&A pairs for Model Fine-Tuning"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export Training Data</span>
          </button>
        </div>
      </div>

      {/* Tab Navigation Pill Bar */}
      <div className="flex items-center gap-2 p-1.5 bg-[#090d16] border border-white/10 rounded-2xl w-fit overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'overview'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
          }`}
        >
          <Activity className="w-4 h-4 shrink-0" />
          <span>Overview &amp; Billing</span>
        </button>

        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'users'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
          }`}
        >
          <Users className="w-4 h-4 shrink-0" />
          <span>User Directory &amp; Chat History</span>
          <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/20 font-mono font-bold">
            {userList.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab('traces')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'traces'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
          }`}
        >
          <Search className="w-4 h-4 shrink-0" />
          <span>Trace Viewer &amp; Chunks</span>
        </button>

        <button
          onClick={() => setActiveTab('faqs')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'faqs'
              ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
          }`}
        >
          <HelpCircle className="w-4 h-4 shrink-0" />
          <span>Frequent Questions &amp; Risk Signals</span>
          {(policyRiskCount > 0 || churnRiskCount > 0) && (
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
          )}
        </button>

        <button
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all cursor-pointer ${
            activeTab === 'catalog'
              ? 'bg-gradient-to-r from-indigo-600 to-cyan-600 text-white shadow-md shadow-indigo-600/30'
              : 'text-slate-400 hover:text-white hover:bg-white/[0.04]'
          }`}
        >
          <Building className="w-4 h-4 shrink-0 text-cyan-400" />
          <span>Company Info &amp; Catalog</span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 font-mono font-bold">
            Hub
          </span>
        </button>
      </div>

      {/* =====================================================================
          TAB 1: OVERVIEW & BILLING
          ===================================================================== */}
      {activeTab === 'overview' && (
        <div className="space-y-8 animate-in fade-in duration-150">
          
          {/* Top 4 KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            
            {/* KPI 1: Total Queries */}
            <div className="p-5 rounded-2xl bg-[#0f1422] border border-white/10 hover:border-indigo-500/40 transition-colors shadow-lg">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
                <span className="font-semibold uppercase tracking-wider">Enterprise Inferences</span>
                <MessageSquare className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-3xl font-extrabold text-white font-['Outfit']">
                {totalQueries.toLocaleString()}
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs text-slate-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>Across {userList.length} registered accounts</span>
              </div>
            </div>

            {/* KPI 2: Total Tokens */}
            <div className="p-5 rounded-2xl bg-[#0f1422] border border-white/10 hover:border-cyan-500/40 transition-colors shadow-lg">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
                <span className="font-semibold uppercase tracking-wider">Cumulative Tokens</span>
                <Coins className="w-4 h-4 text-cyan-400" />
              </div>
              <div className="text-3xl font-extrabold text-white font-['Outfit']">
                {totalTokens.toLocaleString()}
              </div>
              <div className="flex items-center gap-2 mt-2 text-xs text-cyan-300">
                <span>{tokenUsagePct}% of {planTokens.toLocaleString()} quota</span>
              </div>
            </div>

            {/* KPI 3: Grounded Accuracy */}
            <div className="p-5 rounded-2xl bg-[#0f1422] border border-white/10 hover:border-emerald-500/40 transition-colors shadow-lg">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
                <span className="font-semibold uppercase tracking-wider">Grounded Precision</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-3xl font-extrabold text-white font-['Outfit']">
                {positiveRate}%
              </div>
              <div className="flex items-center gap-1.5 mt-2 text-xs text-emerald-400">
                <Award className="w-3.5 h-3.5" />
                <span>Zero Hallucination Guardrails Active</span>
              </div>
            </div>

            {/* KPI 4: P95 Latency SLA */}
            <div className="p-5 rounded-2xl bg-[#0f1422] border border-white/10 hover:border-amber-500/40 transition-colors shadow-lg">
              <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
                <span className="font-semibold uppercase tracking-wider">P95 SLA Latency</span>
                <Clock className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-3xl font-extrabold text-white font-['Outfit']">
                {p95Latency} ms
              </div>
              <div className="text-xs text-slate-400 mt-2 font-mono">
                P50: {p50Latency} ms &bull; Sub-second Target
              </div>
            </div>

          </div>

          {/* Billing & Quota Progress Box */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-[#0c101a] via-[#0f1424] to-[#12192e] border border-indigo-500/30 shadow-xl space-y-6">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shadow-md">
                  <CreditCard className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-['Outfit']">
                    Enterprise Quota &amp; Spend Telemetry
                  </h3>
                  <p className="text-xs text-slate-400">
                    Calculated consumption based on PostgreSQL token audit logs.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-right">
                <div>
                  <div className="text-xs text-slate-400">Current Cost Incurred</div>
                  <div className="text-xl font-bold text-emerald-400 font-mono">
                    {currencySymbol}{billedAmount}
                  </div>
                </div>
                <div className="h-8 w-px bg-white/10" />
                <div>
                  <div className="text-xs text-slate-400">Cost per Query</div>
                  <div className="text-xl font-bold text-cyan-400 font-mono">
                    {currencySymbol}{costPerQuery}
                  </div>
                </div>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-mono text-slate-300">
                <span>Consumed: {totalTokens.toLocaleString()} tokens</span>
                <span>Remaining: {remainingTokens.toLocaleString()} tokens</span>
              </div>
              <div className="w-full h-3 rounded-full bg-white/5 overflow-hidden p-0.5 border border-white/10">
                <div 
                  className="h-full rounded-full bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 transition-all duration-500 shadow-sm"
                  style={{ width: `${Math.min(Number(tokenUsagePct), 100)}%` }}
                />
              </div>
            </div>

            {/* Budget Customizer Form */}
            <form onSubmit={handleSaveBudget} className="pt-4 border-t border-white/10 flex flex-wrap items-end gap-3 text-xs">
              <div>
                <label className="block text-slate-400 mb-1">Contract Quota Tokens</label>
                <input
                  type="number"
                  value={planTokens}
                  onChange={(e) => setPlanTokens(Number(e.target.value))}
                  className="px-3 py-1.5 bg-white/[0.04] border border-white/10 rounded-lg text-white font-mono w-36 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Plan Price</label>
                <input
                  type="number"
                  value={planPrice}
                  onChange={(e) => setPlanPrice(Number(e.target.value))}
                  className="px-3 py-1.5 bg-white/[0.04] border border-white/10 rounded-lg text-white font-mono w-28 focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-slate-400 mb-1">Currency</label>
                <input
                  type="text"
                  value={currencySymbol}
                  onChange={(e) => setCurrencySymbol(e.target.value)}
                  className="px-3 py-1.5 bg-white/[0.04] border border-white/10 rounded-lg text-white font-mono w-16 text-center focus:outline-none focus:border-indigo-500"
                />
              </div>
              <button
                type="submit"
                className="py-1.5 px-3 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/30 font-semibold cursor-pointer"
              >
                Save Contract
              </button>
            </form>
          </div>

          {/* Query Intelligence & Semantic Cache Performance Card */}
          <div className="p-6 rounded-2xl bg-[#0f1422] border border-white/10 shadow-xl space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white font-['Outfit'] flex flex-wrap items-center gap-2">
                    <span>Query Intelligence &amp; Semantic Cache Layer</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                      ACTIVE
                    </span>
                    {cacheStats?.redis_connected ? (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 font-mono font-bold flex items-center gap-1.5 border border-rose-500/30 shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse"></span>
                        REDIS / MEMURAI ONLINE ({cacheStats?.redis_memory || '<1MB'})
                      </span>
                    ) : (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-500/20 text-slate-400 font-mono">
                        DATABASE CACHE
                      </span>
                    )}
                  </h3>
                  <p className="text-xs text-slate-400">
                    Shorthand rewriting, scope safety gating, Redis sub-2ms exact hits &amp; &ge;90%–95% direct semantic cache hits
                  </p>
                </div>
              </div>

              <button
                onClick={handleClearCache}
                disabled={isClearingCache}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-rose-500/20 border border-white/10 hover:border-rose-500/40 text-slate-300 hover:text-rose-300 text-xs font-semibold transition-all cursor-pointer"
              >
                <RotateCw className={`w-3.5 h-3.5 ${isClearingCache ? 'animate-spin' : ''}`} />
                <span>Flush Cache</span>
              </button>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-1">
              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Cached Patterns</div>
                <div className="text-xl font-bold text-white font-mono mt-1">
                  {cacheStats?.total_cached_patterns || 0}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">Safe scope-gated entries</div>
              </div>

              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Cache Hit Rate</div>
                <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
                  {cacheStats?.cache_hit_rate_pct || 0}%
                </div>
                <div className="text-[10px] text-slate-500 mt-1">Repeated query reuse</div>
              </div>

              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Redis Fast Hits</div>
                <div className="text-xl font-bold text-rose-400 font-mono mt-1">
                  {cacheStats?.redis_hits || 0}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">&lt;2ms instant answers</div>
              </div>

              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Direct Hit Threshold</div>
                <div className="text-xl font-bold text-indigo-400 font-mono mt-1">
                  {cacheStats?.similarity_threshold ? `${Math.round(cacheStats.similarity_threshold * 100)}%` : '92%'}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">90%–95% query relevance</div>
              </div>

              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Latency Saved</div>
                <div className="text-xl font-bold text-cyan-400 font-mono mt-1">
                  {cacheStats?.total_latency_saved_ms ? `${(cacheStats.total_latency_saved_ms / 1000).toFixed(1)}s` : '0.0s'}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">LLM turnaround avoided</div>
              </div>

              <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="text-[11px] font-semibold text-slate-400 uppercase">Total Spend Saved</div>
                <div className="text-xl font-bold text-amber-400 font-mono mt-1">
                  ${cacheStats?.total_cost_saved_usd || '0.0000'}
                </div>
                <div className="text-[10px] text-slate-500 mt-1">Token charges avoided</div>
              </div>
            </div>
          </div>

        </div>
      )}

      {/* =====================================================================
          TAB 2: USER DIRECTORY & CHAT HISTORY (USER SECTION)
          ===================================================================== */}
      {activeTab === 'users' && (
        <div className="space-y-6 animate-in fade-in duration-150">
          
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* User Directory Column */}
            <div className="lg:col-span-4 xl:col-span-3 space-y-4">
              <div className="flex items-center justify-between pb-1">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Users className="w-4 h-4 text-indigo-400" />
                  <span>Registered Users ({userList.length})</span>
                </h3>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-300 font-mono border border-blue-500/20">
                  PostgreSQL
                </span>
              </div>

              <div className="space-y-2">
                {userList.map((u) => {
                  const isSelected = selectedUser === u.username;
                  return (
                    <div
                      key={u.id}
                      onClick={() => {
                        setSelectedUser(u.username);
                        setMobileChatView('list');
                      }}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${
                        isSelected
                          ? 'bg-gradient-to-r from-indigo-950/70 to-indigo-900/40 border-indigo-500 shadow-lg shadow-indigo-950/50 ring-1 ring-indigo-500/30'
                          : 'bg-[#0b0f19] border-white/10 hover:border-white/20 hover:bg-white/[0.02]'
                      }`}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm shrink-0 shadow-sm ${
                          u.role === 'admin'
                            ? 'bg-amber-500 text-black'
                            : 'bg-indigo-600 text-white'
                        }`}>
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-sm font-bold text-white truncate">{u.username}</span>
                            <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold uppercase ${
                              u.role === 'admin'
                                ? 'bg-amber-500/20 text-amber-300'
                                : 'bg-cyan-500/20 text-cyan-300'
                            }`}>
                              {u.role}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 font-mono truncate block">{u.email}</span>
                        </div>
                      </div>

                      <div className="text-right shrink-0 ml-2">
                        <div className="text-xs font-bold text-cyan-400 font-mono">
                          {u.total_tokens.toLocaleString()} tok
                        </div>
                        <div className="text-[10px] text-slate-400 font-mono">
                          {u.query_count} queries
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Login Switcher Helper Box */}
              <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10 text-xs text-slate-400 space-y-2">
                <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
                  <UserCheck className="w-4 h-4 text-emerald-400" />
                  <span>Simulate Another User</span>
                </div>
                <p className="text-[11px]">
                  Want to test queries as <strong>admin</strong>, <strong>test1</strong>, or <strong>test2</strong>?
                </p>
                <button
                  type="button"
                  onClick={onOpenAuthModal}
                  className="w-full py-1.5 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/30 text-xs font-semibold cursor-pointer transition-colors"
                >
                  Open Account Switcher
                </button>
              </div>

            </div>

            {/* Individual User Chat History Column: Side-by-Side Master-Detail */}
            <div className="lg:col-span-8 xl:col-span-9 space-y-4">
              
              {/* Header Bar for Selected User */}
              <div className="p-4 rounded-2xl bg-[#0b0f19] border border-white/10 flex flex-wrap items-center justify-between gap-3 shadow-lg">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-white font-bold text-sm shadow-md">
                    <MessageSquare className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                        Chat Provenance for <span className="text-indigo-400 font-mono">@{selectedUser}</span>
                      </h3>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono font-bold">
                        {userChatHistory.length} turns
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Select any conversation from the list to inspect turn-by-turn queries, AI answers, and chunk attribution side-by-side.
                    </p>
                  </div>
                </div>

                {/* Search & Filter Toolbar */}
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      placeholder="Filter conversations..."
                      value={chatSearchQuery}
                      onChange={(e) => setChatSearchQuery(e.target.value)}
                      className="pl-8 pr-3 py-1.5 bg-black/40 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono w-48 sm:w-56"
                    />
                  </div>

                  <button
                    type="button"
                    onClick={() => setChatRiskFilterOnly(!chatRiskFilterOnly)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                      chatRiskFilterOnly
                        ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-sm'
                        : 'bg-white/[0.04] text-slate-400 border-white/10 hover:text-white hover:bg-white/[0.08]'
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Risk Only</span>
                  </button>
                </div>
              </div>

              {historyLoading ? (
                <div className="p-16 rounded-2xl bg-[#0b0f19] border border-white/10 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
                  <RotateCw className="w-6 h-6 animate-spin text-indigo-400" />
                  <span className="font-medium">Loading chat history from PostgreSQL...</span>
                </div>
              ) : userChatHistory.length === 0 ? (
                <div className="p-16 rounded-2xl bg-[#0b0f19] border border-white/10 text-center space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center mx-auto">
                    <MessageSquare className="w-6 h-6" />
                  </div>
                  <h4 className="text-white text-base font-semibold">No queries recorded yet for @{selectedUser}</h4>
                  <p className="text-slate-400 text-xs max-w-md mx-auto">
                    Switch to this account in the Search page to ask questions and review their multi-turn traces and citations here.
                  </p>
                </div>
              ) : (
                (() => {
                  // Process session threads
                  const sessionMap = {};
                  userChatHistory.forEach((msg) => {
                    const sid = msg.session_id || 'default_session';
                    if (!sessionMap[sid]) {
                      sessionMap[sid] = {
                        sessionId: sid,
                        turns: [],
                        totalTokens: 0,
                        totalCost: 0,
                        lastActivity: msg.created_at,
                        hasRisk: false,
                      };
                    }
                    sessionMap[sid].turns.push(msg);
                    sessionMap[sid].totalTokens += (msg.total_tokens || 0);
                    sessionMap[sid].totalCost += (msg.cost_usd || 0);
                    if (msg.policy_risk_flag || msg.churn_risk_flag) {
                      sessionMap[sid].hasRisk = true;
                    }
                  });

                  const allSessionThreads = Object.values(sessionMap);
                  allSessionThreads.forEach((sess) => {
                    sess.turns.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                    sess.firstQuery = sess.turns[0]?.query || 'Conversation';
                  });
                  allSessionThreads.sort((a, b) => new Date(b.lastActivity) - new Date(a.lastActivity));

                  const filteredSessionThreads = allSessionThreads.filter((sess) => {
                    if (chatRiskFilterOnly && !sess.hasRisk) return false;
                    if (chatSearchQuery.trim()) {
                      const q = chatSearchQuery.toLowerCase();
                      const queryMatch = sess.turns.some(
                        (t) => (t.query && t.query.toLowerCase().includes(q)) || (t.answer && t.answer.toLowerCase().includes(q))
                      );
                      const idMatch = sess.sessionId.toLowerCase().includes(q);
                      return queryMatch || idMatch;
                    }
                    return true;
                  });

                  // Active selected thread (side way view)
                  const activeSession = filteredSessionThreads.find((s) => s.sessionId === selectedSessionId)
                    || filteredSessionThreads[0]
                    || allSessionThreads.find((s) => s.sessionId === selectedSessionId)
                    || allSessionThreads[0]
                    || null;

                  return (
                    <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
                      
                      {/* Left: Interactive List of Conversations */}
                      <div className={`md:col-span-5 lg:col-span-5 xl:col-span-4 space-y-3 ${
                        mobileChatView === 'chat' ? 'hidden md:block' : 'block'
                      }`}>
                        <div className="flex items-center justify-between text-xs font-semibold text-slate-300 px-1">
                          <span className="uppercase tracking-wider flex items-center gap-1.5 text-slate-400">
                            <Layers className="w-3.5 h-3.5 text-indigo-400" />
                            <span>Conversations ({filteredSessionThreads.length})</span>
                          </span>
                          <span className="text-[11px] text-slate-500 font-mono">
                            {allSessionThreads.length} total
                          </span>
                        </div>

                        {filteredSessionThreads.length === 0 ? (
                          <div className="p-8 rounded-xl bg-[#0b0f19] border border-white/10 text-center text-xs text-slate-400 space-y-1">
                            <p className="font-semibold text-slate-300">No matching conversations</p>
                            <p className="text-[11px] text-slate-500">Try adjusting your filter or search query.</p>
                          </div>
                        ) : (
                          <div className="space-y-2 max-h-[740px] overflow-y-auto pr-1">
                            {filteredSessionThreads.map((thread) => {
                              const isSelected = activeSession?.sessionId === thread.sessionId;
                              const dateStr = thread.lastActivity 
                                ? `${thread.lastActivity.split('T')[0]} ${thread.lastActivity.split('T')[1]?.slice(0, 5) || ''}`
                                : 'Recent';

                              return (
                                <div
                                  key={thread.sessionId}
                                  onClick={() => {
                                    setSelectedSessionId(thread.sessionId);
                                    setMobileChatView('chat');
                                  }}
                                  className={`p-3.5 rounded-xl border transition-all cursor-pointer relative group text-left ${
                                    isSelected
                                      ? 'bg-gradient-to-r from-indigo-950/70 via-indigo-900/40 to-[#0c1120] border-indigo-500 shadow-md shadow-indigo-950/40 ring-1 ring-indigo-500/30'
                                      : 'bg-[#0b0f19] border-white/10 hover:border-white/20 hover:bg-white/[0.02]'
                                  }`}
                                >
                                  {/* Left accent bar for active */}
                                  {isSelected && (
                                    <div className="absolute left-0 top-2 bottom-2 w-1 bg-gradient-to-b from-indigo-400 to-cyan-400 rounded-r" />
                                  )}

                                  <div className="space-y-2 pl-1">
                                    <div className="flex items-center justify-between gap-2">
                                      <span className="text-[10px] px-2 py-0.5 rounded bg-white/[0.06] text-slate-300 font-mono font-medium truncate max-w-[140px]">
                                        {thread.sessionId}
                                      </span>
                                      <span className="text-[10px] text-slate-400 font-mono shrink-0">
                                        {dateStr}
                                      </span>
                                    </div>

                                    <h4 className="text-xs font-semibold text-white group-hover:text-indigo-300 transition-colors line-clamp-2 leading-relaxed">
                                      "{thread.firstQuery}"
                                    </h4>

                                    <div className="flex items-center justify-between pt-1 border-t border-white/5 text-[10px] font-mono">
                                      <div className="flex items-center gap-2">
                                        <span className="text-slate-400">
                                          💬 {thread.turns.length} {thread.turns.length === 1 ? 'prompt' : 'prompts'}
                                        </span>
                                        <span className="text-slate-600">&bull;</span>
                                        <span className="text-cyan-400 font-semibold">
                                          {thread.totalTokens.toLocaleString()}t
                                        </span>
                                      </div>

                                      <div className="flex items-center gap-1.5">
                                        {thread.hasRisk && (
                                          <span className="px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-bold">
                                            RISK
                                          </span>
                                        )}
                                        <ChevronRight className={`w-3.5 h-3.5 transition-transform ${
                                          isSelected ? 'text-indigo-400 translate-x-0.5' : 'text-slate-500 group-hover:text-slate-300'
                                        }`} />
                                      </div>
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      {/* Right: Selected Chat View (Side Way) */}
                      <div className={`md:col-span-7 lg:col-span-7 xl:col-span-8 space-y-3 ${
                        mobileChatView === 'list' ? 'hidden md:block' : 'block'
                      }`}>
                        
                        {activeSession ? (
                          <div className="rounded-2xl bg-[#080d19] border border-white/10 shadow-2xl overflow-hidden flex flex-col">
                            
                            {/* Chat Header */}
                            <div className="p-4 bg-white/[0.02] border-b border-white/10 flex flex-wrap items-center justify-between gap-3 shrink-0">
                              <div className="flex items-center gap-2">
                                {/* Mobile Back Button */}
                                <button
                                  type="button"
                                  onClick={() => setMobileChatView('list')}
                                  className="md:hidden p-1.5 rounded-lg bg-white/5 text-slate-300 hover:text-white mr-1 cursor-pointer"
                                >
                                  <ArrowLeft className="w-4 h-4" />
                                </button>
                                
                                <div className="space-y-0.5">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-xs font-mono font-bold text-indigo-300 flex items-center gap-1.5">
                                      <span>Session:</span>
                                      <span className="text-white">{activeSession.sessionId}</span>
                                    </span>
                                    <button
                                      type="button"
                                      onClick={() => handleCopyAuditText(activeSession.sessionId, activeSession.sessionId)}
                                      title="Copy Session ID"
                                      className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/5 transition-colors cursor-pointer"
                                    >
                                      {copiedAuditText === activeSession.sessionId ? (
                                        <Check className="w-3.5 h-3.5 text-emerald-400" />
                                      ) : (
                                        <Copy className="w-3.5 h-3.5" />
                                      )}
                                    </button>
                                    {activeSession.hasRisk && (
                                      <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-mono font-bold">
                                        RISK DETECTED
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-[11px] text-slate-400 font-mono">
                                    Last active: {activeSession.lastActivity?.replace('T', ' ').slice(0, 16)}
                                  </p>
                                </div>
                              </div>

                              <div className="flex items-center gap-3 text-xs font-mono">
                                <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] text-slate-300">
                                  💬 {activeSession.turns.length} {activeSession.turns.length === 1 ? 'Prompt' : 'Prompts'}
                                </span>
                                <span className="px-2.5 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 font-bold">
                                  {activeSession.totalTokens.toLocaleString()} tok
                                </span>
                              </div>
                            </div>

                            {/* Chat Message Stream */}
                            <div className="p-4 sm:p-5 space-y-6 max-h-[660px] overflow-y-auto">
                              {activeSession.turns.map((item, turnIdx) => {
                                const isExpanded = expandedMessageId === item.id;
                                const chunks = item.chunks_sent || [];
                                const citations = item.citations || [];

                                return (
                                  <div key={item.id} className="space-y-3.5 relative">
                                    
                                    {turnIdx > 0 && (
                                      <div className="w-full border-t border-white/5 my-4" />
                                    )}

                                    {/* Turn Sub-Header */}
                                    <div className="flex items-center justify-between text-xs">
                                      <div className="flex items-center gap-2">
                                        <span className="w-5 h-5 rounded-full bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 font-mono font-bold text-[10px] flex items-center justify-center">
                                          {turnIdx + 1}
                                        </span>
                                        <span className="text-slate-300 font-semibold text-[11px]">Prompt #{turnIdx + 1}</span>
                                        <span className="text-[10px] text-slate-500 font-mono truncate max-w-[120px]">{item.trace_id}</span>
                                      </div>

                                      <div className="flex items-center gap-2 text-right text-[11px] font-mono">
                                        <span className="text-emerald-400 font-bold">{item.total_latency_ms}ms</span>
                                        <span className="text-slate-600">&bull;</span>
                                        <span className="text-slate-400">{item.total_tokens} tok</span>
                                      </div>
                                    </div>

                                    {/* User Question */}
                                    <div className="p-4 rounded-xl bg-gradient-to-r from-indigo-950/40 to-slate-900/60 border border-indigo-500/30 text-white text-xs font-medium space-y-1.5 shadow-sm">
                                      <div className="flex items-center justify-between text-[10px] text-indigo-300 font-mono uppercase tracking-wider font-semibold">
                                        <span className="flex items-center gap-1.5">
                                          <User className="w-3.5 h-3.5" />
                                          <span>User Prompt</span>
                                        </span>
                                        <div className="flex items-center gap-2">
                                          <button
                                            type="button"
                                            onClick={() => handleCopyAuditText(item.query, `q_${item.id}`)}
                                            className="text-slate-400 hover:text-white transition-colors cursor-pointer"
                                            title="Copy prompt"
                                          >
                                            {copiedAuditText === `q_${item.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                                          </button>
                                          {onRerunQuery && (
                                            <button
                                              type="button"
                                              onClick={() => onRerunQuery(item.query)}
                                              className="text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
                                              title="Rerun this query in Search"
                                            >
                                              <ArrowRight className="w-3 h-3" />
                                            </button>
                                          )}
                                        </div>
                                      </div>
                                      <p className="text-slate-100 font-sans text-sm leading-relaxed whitespace-pre-wrap">{item.query}</p>
                                    </div>

                                    {/* Assistant Generated Response */}
                                    <div className="p-4 sm:p-5 rounded-xl bg-black/50 border border-white/10 space-y-3.5 text-xs text-slate-300 font-sans leading-relaxed shadow-md">
                                      <div className="flex items-center justify-between text-[11px] font-semibold text-cyan-400 border-b border-white/5 pb-2">
                                        <span className="flex items-center gap-1.5">
                                          <Bot className="w-4 h-4 text-cyan-400" />
                                          <span>AI Grounded Response</span>
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => handleCopyAuditText(item.answer, `a_${item.id}`)}
                                          className="flex items-center gap-1 text-[10px] font-mono text-slate-400 hover:text-white transition-colors cursor-pointer"
                                        >
                                          {copiedAuditText === `a_${item.id}` ? (
                                            <>
                                              <Check className="w-3 h-3 text-emerald-400" />
                                              <span className="text-emerald-400">Copied</span>
                                            </>
                                          ) : (
                                            <>
                                              <Copy className="w-3 h-3" />
                                              <span>Copy Answer</span>
                                            </>
                                          )}
                                        </button>
                                      </div>

                                      {/* Markdown Content */}
                                      <div 
                                        className="ragops-markdown max-w-none text-slate-200"
                                        dangerouslySetInnerHTML={{ __html: marked.parse(item.answer || '') }}
                                      />

                                      {/* Citations & Chunks Inspection Toggle */}
                                      <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-white/5 text-xs">
                                        <div className="flex flex-wrap items-center gap-1.5 text-slate-400 text-[11px]">
                                          <span className="font-semibold text-slate-300">Citations:</span>
                                          {citations.length > 0 ? (
                                            citations.map((c, i) => (
                                              <span 
                                                key={i} 
                                                onClick={() => onChunkClick && onChunkClick(c)}
                                                className={`px-2 py-0.5 rounded bg-white/[0.05] text-[10px] text-cyan-300 font-mono border border-white/5 ${
                                                  onChunkClick ? 'hover:border-cyan-500/40 hover:bg-cyan-500/10 cursor-pointer' : ''
                                                }`}
                                              >
                                                {c.document} {c.page ? `p.${c.page}` : ''}
                                              </span>
                                            ))
                                          ) : (
                                            <span className="text-[11px] text-slate-500 italic">No citations</span>
                                          )}
                                        </div>

                                        <button
                                          type="button"
                                          onClick={() => setExpandedMessageId(isExpanded ? null : item.id)}
                                          className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-xs font-semibold cursor-pointer py-1 px-2 rounded-lg hover:bg-indigo-500/10 transition-colors"
                                        >
                                          <span>{isExpanded ? 'Hide' : 'Inspect'} Chunks ({chunks.length})</span>
                                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                        </button>
                                      </div>

                                      {/* Collapsible Chunks Sent to LLM */}
                                      {isExpanded && (
                                        <div className="mt-3 p-3.5 rounded-xl bg-[#07090e] border border-white/10 space-y-2.5 animate-in fade-in duration-150">
                                          <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-1 flex items-center justify-between">
                                            <span>Retrieved Grounding Chunks Context:</span>
                                            <span className="text-[10px] font-mono text-slate-500">{chunks.length} chunks</span>
                                          </div>
                                          {chunks.length === 0 ? (
                                            <p className="text-xs text-slate-500 italic">No chunk data stored for this turn.</p>
                                          ) : (
                                            <div className="space-y-2">
                                              {chunks.map((chk, cIdx) => (
                                                <div 
                                                  key={cIdx} 
                                                  onClick={() => onChunkClick && onChunkClick(chk)}
                                                  className={`p-3 rounded-lg bg-white/[0.02] border border-white/5 space-y-1.5 ${
                                                    onChunkClick ? 'hover:border-cyan-500/40 hover:bg-cyan-500/5 cursor-pointer' : ''
                                                  }`}
                                                >
                                                  <div className="flex items-center justify-between text-[11px] font-mono">
                                                    <span className="text-indigo-400 font-semibold truncate max-w-[280px]">
                                                      [{cIdx + 1}] {chk.source || 'doc'} {chk.page ? `(p.${chk.page})` : ''}
                                                    </span>
                                                    <span className="text-emerald-400 font-bold shrink-0">
                                                      Score: {chk.score ? `${Math.round(chk.score * 100)}%` : 'Grounded'}
                                                    </span>
                                                  </div>
                                                  <p className="text-[11px] text-slate-400 line-clamp-3 font-mono leading-relaxed">
                                                    {chk.text || 'No text snippet'}
                                                  </p>
                                                </div>
                                              ))}
                                            </div>
                                          )}

                                          <div className="pt-2 border-t border-white/5 grid grid-cols-4 gap-2 text-[10px] font-mono text-center text-slate-400">
                                            <div className="p-1 rounded bg-white/[0.02]">Embed: <span className="text-white font-bold">{item.embed_latency_ms}ms</span></div>
                                            <div className="p-1 rounded bg-white/[0.02]">Search: <span className="text-white font-bold">{item.search_latency_ms}ms</span></div>
                                            <div className="p-1 rounded bg-white/[0.02]">Rerank: <span className="text-white font-bold">{item.rerank_latency_ms}ms</span></div>
                                            <div className="p-1 rounded bg-white/[0.02]">LLM: <span className="text-white font-bold">{item.generation_latency_ms}ms</span></div>
                                          </div>
                                        </div>
                                      )}
                                    </div>

                                  </div>
                                );
                              })}
                            </div>

                          </div>
                        ) : (
                          <div className="p-16 rounded-2xl bg-[#080d19] border border-white/10 text-center space-y-2">
                            <p className="text-slate-300 text-sm font-semibold">Select a conversation</p>
                            <p className="text-slate-500 text-xs">Choose any conversation from the list to view its chat provenance.</p>
                          </div>
                        )}

                      </div>

                    </div>
                  );
                })()
              )}

            </div>

          </div>

        </div>
      )}

      {/* =====================================================================
          TAB 3: TRACE VIEWER & RETRIEVAL INSPECTOR
          ===================================================================== */}
      {activeTab === 'traces' && (
        <div className="space-y-6 animate-in fade-in duration-150">
          
          {/* Header & Controls Toolbar */}
          <div className="p-5 rounded-2xl bg-[#0b0f19] border border-white/10 space-y-4 shadow-xl">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Search className="w-5 h-5 text-indigo-400" />
                  <span>Distributed Request Tracing &amp; Retrieval Inspector</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Inspect query execution hops, token telemetry, and click any trace to expand its AI response &amp; latency waterfall.
                </p>
              </div>

              {/* Action Buttons: Expand All & Collapse All */}
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => handleExpandAllTraces(recentLogs)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/10 text-xs font-semibold cursor-pointer transition-colors"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                  <span>Expand All</span>
                </button>
                <button
                  type="button"
                  onClick={handleCollapseAllTraces}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/10 text-xs font-semibold cursor-pointer transition-colors"
                >
                  <Minimize2 className="w-3.5 h-3.5" />
                  <span>Collapse All</span>
                </button>
              </div>
            </div>

            {/* Filter and Search Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-white/5">
              <div className="flex items-center gap-2 flex-wrap">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Search traces by query, @user, or trace ID..."
                    value={traceSearchQuery}
                    onChange={(e) => setTraceSearchQuery(e.target.value)}
                    className="pl-8 pr-3 py-1.5 bg-black/40 border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono w-56 sm:w-72"
                  />
                </div>

                {/* Filter Pills */}
                <button
                  type="button"
                  onClick={() => {
                    setTraceLatencyFilter('all');
                    setRiskFilter(false);
                  }}
                  className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    traceLatencyFilter === 'all' && !riskFilter
                      ? 'bg-indigo-600 text-white border-indigo-500 shadow-sm'
                      : 'bg-white/[0.04] text-slate-400 border-white/10 hover:text-white'
                  }`}
                >
                  All ({recentLogs.length})
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setRiskFilter(!riskFilter);
                  }}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    riskFilter
                      ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 shadow-sm'
                      : 'bg-white/[0.04] text-slate-400 border-white/10 hover:text-white'
                  }`}
                >
                  <ShieldAlert className="w-3.5 h-3.5" />
                  <span>Risk Signals</span>
                </button>

                <button
                  type="button"
                  onClick={() => setTraceLatencyFilter(traceLatencyFilter === 'slow' ? 'all' : 'slow')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                    traceLatencyFilter === 'slow'
                      ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm'
                      : 'bg-white/[0.04] text-slate-400 border-white/10 hover:text-white'
                  }`}
                >
                  <Clock className="w-3.5 h-3.5" />
                  <span>Slow (&gt;1.5s)</span>
                </button>
              </div>

              <div className="text-xs text-slate-400 font-mono">
                Showing {
                  recentLogs.filter((log) => {
                    if (riskFilter && !log.policy_risk_flag && !log.churn_risk_flag) return false;
                    if (traceLatencyFilter === 'slow' && (log.total_latency_ms || 0) < 1500) return false;
                    if (traceSearchQuery.trim()) {
                      const q = traceSearchQuery.toLowerCase();
                      const queryMatch = log.query && log.query.toLowerCase().includes(q);
                      const userMatch = log.username && log.username.toLowerCase().includes(q);
                      const idMatch = log.trace_id && log.trace_id.toLowerCase().includes(q);
                      const ansMatch = log.answer && log.answer.toLowerCase().includes(q);
                      return queryMatch || userMatch || idMatch || ansMatch;
                    }
                    return true;
                  }).length
                } of {recentLogs.length} traces
              </div>
            </div>
          </div>

          {/* Compact Space-Saving Trace Cards with Click-to-Expand AI Response */}
          <div className="space-y-3">
            {recentLogs
              .filter((log) => {
                if (riskFilter && !log.policy_risk_flag && !log.churn_risk_flag) return false;
                if (traceLatencyFilter === 'slow' && (log.total_latency_ms || 0) < 1500) return false;
                if (traceSearchQuery.trim()) {
                  const q = traceSearchQuery.toLowerCase();
                  const queryMatch = log.query && log.query.toLowerCase().includes(q);
                  const userMatch = log.username && log.username.toLowerCase().includes(q);
                  const idMatch = log.trace_id && log.trace_id.toLowerCase().includes(q);
                  const ansMatch = log.answer && log.answer.toLowerCase().includes(q);
                  return queryMatch || userMatch || idMatch || ansMatch;
                }
                return true;
              })
              .map((log) => {
                const logKey = log.id || log.trace_id;
                const isExpanded = Boolean(expandedTraceIds[logKey]);

                // Latency color code
                const latency = log.total_latency_ms || 0;
                const latencyBadgeColor = latency < 1000 
                  ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                  : latency < 2500 
                    ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                    : 'bg-rose-500/15 text-rose-300 border-rose-500/30';

                return (
                  <div 
                    key={logKey}
                    className={`rounded-xl border transition-all overflow-hidden ${
                      isExpanded
                        ? 'bg-[#0d1222] border-indigo-500/50 shadow-xl ring-1 ring-indigo-500/20'
                        : 'bg-[#0b0f19] border-white/10 hover:border-indigo-500/30 hover:bg-white/[0.01]'
                    }`}
                  >
                    {/* Compact Card Header: Always Visible ("Show necessary info above") */}
                    <div 
                      onClick={() => toggleTraceExpand(logKey)}
                      className="p-4 cursor-pointer select-none space-y-2.5"
                    >
                      {/* Top Row: Metadata badges */}
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-2 text-xs">
                          <span className="font-mono text-indigo-300 font-semibold flex items-center gap-1">
                            <span>{log.trace_id}</span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleCopyTraceText(log.trace_id, log.trace_id);
                              }}
                              className="p-0.5 text-slate-500 hover:text-white transition-colors cursor-pointer"
                              title="Copy trace ID"
                            >
                              {copiedTraceText === log.trace_id ? (
                                <Check className="w-3 h-3 text-emerald-400" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </span>
                          <span className="text-slate-600">&bull;</span>
                          <span className="px-2 py-0.5 rounded bg-white/[0.06] font-mono text-slate-300 font-semibold flex items-center gap-1">
                            <User className="w-3 h-3 text-slate-400" />
                            <span>@{log.username}</span>
                          </span>
                          <span className="text-slate-600">&bull;</span>
                          <span className="text-slate-400 font-mono text-[11px]">{log.created_at}</span>
                          
                          {/* Risk Badges */}
                          {log.policy_risk_flag && (
                            <span className="px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 text-[10px] font-mono font-bold">
                              POLICY RISK
                            </span>
                          )}
                          {log.churn_risk_flag && (
                            <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 text-[10px] font-mono font-bold">
                              CHURN RISK
                            </span>
                          )}
                        </div>

                        {/* Latency and Token Badges */}
                        <div className="flex items-center gap-2.5 text-xs font-mono">
                          <span className="text-slate-400 hidden sm:inline">
                            In: {log.input_tokens || 0}t &bull; Out: {log.output_tokens || 0}t
                          </span>
                          <span className={`px-2.5 py-0.5 rounded-full border text-xs font-bold font-mono ${latencyBadgeColor}`}>
                            {latency}ms
                          </span>
                        </div>
                      </div>

                      {/* Bottom Row: Query & Expand Toggle Button */}
                      <div className="flex items-center justify-between gap-3">
                        <div className="text-sm font-semibold text-white truncate max-w-3xl flex items-center gap-2">
                          <Search className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                          <span className="truncate">"{log.query}"</span>
                        </div>

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleTraceExpand(logKey);
                          }}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all shrink-0 cursor-pointer ${
                            isExpanded
                              ? 'bg-indigo-600/30 text-indigo-300 border-indigo-500/40'
                              : 'bg-white/[0.04] text-slate-300 border-white/10 hover:bg-white/[0.08] hover:text-white'
                          }`}
                        >
                          <span>{isExpanded ? 'Hide Response' : 'View AI Response'}</span>
                          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>

                    {/* Collapsible Area: "After click show response generate by ai so like save space" */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-1 space-y-4 border-t border-white/5 animate-in fade-in duration-150">
                        
                        {/* AI Generated Response */}
                        <div className="p-4 rounded-xl bg-black/50 border border-white/10 space-y-2.5 text-xs text-slate-300 font-sans shadow-inner">
                          <div className="flex items-center justify-between text-[11px] font-semibold text-cyan-400 border-b border-white/5 pb-2">
                            <span className="flex items-center gap-1.5">
                              <Bot className="w-4 h-4 text-cyan-400" />
                              <span>AI Generated Grounded Response:</span>
                            </span>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => handleCopyTraceText(log.answer, `ans_${logKey}`)}
                                className="flex items-center gap-1 text-[10px] font-mono text-slate-400 hover:text-white transition-colors cursor-pointer"
                              >
                                {copiedTraceText === `ans_${logKey}` ? (
                                  <>
                                    <Check className="w-3 h-3 text-emerald-400" />
                                    <span className="text-emerald-400">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy className="w-3 h-3" />
                                    <span>Copy Answer</span>
                                  </>
                                )}
                              </button>
                              {onRerunQuery && (
                                <button
                                  type="button"
                                  onClick={() => onRerunQuery(log.query)}
                                  className="flex items-center gap-1 text-[10px] font-mono text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer"
                                >
                                  <ArrowRight className="w-3 h-3" />
                                  <span>Rerun Query</span>
                                </button>
                              )}
                            </div>
                          </div>

                          <div 
                            className="ragops-markdown max-w-none text-slate-200"
                            dangerouslySetInnerHTML={{ __html: marked.parse(log.answer || 'No response recorded.') }}
                          />
                        </div>

                        {/* Latency Waterfall Bar */}
                        <div className="space-y-1.5 p-3 rounded-xl bg-white/[0.02] border border-white/5">
                          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                            <span className="font-semibold text-slate-300">Latency Breakdown (Waterfall)</span>
                            <span className="text-emerald-400 font-bold">Total: {log.total_latency_ms}ms</span>
                          </div>
                          <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden flex">
                            <div 
                              title={`Embedding: ${log.embed_latency_ms}ms`}
                              style={{ width: `${Math.max(((log.embed_latency_ms || 0) / (log.total_latency_ms || 1)) * 100, 5)}%` }}
                              className="bg-purple-500 h-full"
                            />
                            <div 
                              title={`Vector Search: ${log.search_latency_ms}ms`}
                              style={{ width: `${Math.max(((log.search_latency_ms || 0) / (log.total_latency_ms || 1)) * 100, 5)}%` }}
                              className="bg-blue-500 h-full"
                            />
                            <div 
                              title={`Reranker: ${log.rerank_latency_ms}ms`}
                              style={{ width: `${Math.max(((log.rerank_latency_ms || 0) / (log.total_latency_ms || 1)) * 100, 5)}%` }}
                              className="bg-cyan-500 h-full"
                            />
                            <div 
                              title={`LLM Generation: ${log.generation_latency_ms}ms`}
                              style={{ width: `${Math.max(((log.generation_latency_ms || 0) / (log.total_latency_ms || 1)) * 100, 20)}%` }}
                              className="bg-emerald-500 h-full"
                            />
                          </div>
                          <div className="flex flex-wrap items-center gap-4 text-[10px] font-mono text-slate-400 pt-1">
                            <span className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded bg-purple-500" /> 
                              <span>Embed: <strong className="text-white">{log.embed_latency_ms}ms</strong></span>
                            </span>
                            <span className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded bg-blue-500" /> 
                              <span>Search: <strong className="text-white">{log.search_latency_ms}ms</strong></span>
                            </span>
                            <span className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded bg-cyan-500" /> 
                              <span>Rerank: <strong className="text-white">{log.rerank_latency_ms}ms</strong></span>
                            </span>
                            <span className="flex items-center gap-1.5">
                              <span className="w-2 h-2 rounded bg-emerald-500" /> 
                              <span>LLM: <strong className="text-white">{log.generation_latency_ms}ms</strong></span>
                            </span>
                          </div>
                        </div>

                      </div>
                    )}

                  </div>
                );
              })}
          </div>

        </div>
      )}

      {/* =====================================================================
          TAB 4: FAQS & RISK / CHURN RADAR
          ===================================================================== */}
      {activeTab === 'faqs' && (
        <div className="space-y-6 animate-in fade-in duration-150">
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            
            {/* Left: Frequently Asked Questions (FAQ) */}
            <div className="p-6 rounded-2xl bg-[#0b0f19] border border-white/10 space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <HelpCircle className="w-5 h-5 text-indigo-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Most Frequently Asked Queries
                  </h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">Semantic Clustering</span>
              </div>

              <div className="space-y-2.5">
                {frequentQueries.length === 0 ? (
                  <p className="text-xs text-slate-500 italic py-4">No frequent queries aggregated yet.</p>
                ) : (
                  frequentQueries.map((item, idx) => (
                    <div 
                      key={idx}
                      className="p-3 rounded-xl bg-white/[0.02] border border-white/5 flex items-center justify-between gap-3 hover:border-indigo-500/30 transition-all cursor-pointer group"
                      onClick={() => onRerunQuery(item.query)}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="w-6 h-6 rounded-full bg-indigo-600/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center font-mono text-xs font-bold shrink-0">
                          {idx + 1}
                        </span>
                        <div>
                          <p className="text-xs font-semibold text-white group-hover:text-indigo-300 transition-colors">
                            {item.query}
                          </p>
                          <span className="text-[10px] text-slate-400 font-mono">
                            Avg Latency: {item.avg_latency_ms}ms
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <span className="px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 font-mono text-xs font-bold">
                          {item.count}x
                        </span>
                        <ArrowRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-white transition-colors" />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right: Risk & Churn Signals (POSH, Policy & Leaving Intent) */}
            <div className="p-6 rounded-2xl bg-[#0b0f19] border border-white/10 space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="w-5 h-5 text-rose-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Compliance, POSH &amp; Churn Signals
                  </h3>
                </div>
                <span className="text-xs text-rose-400 font-mono font-bold">
                  {policyRiskCount + churnRiskCount} Alerts
                </span>
              </div>

              <div className="space-y-3">
                {recentLogs.filter(l => l.policy_risk_flag || l.churn_risk_flag).length === 0 ? (
                  <div className="p-8 text-center text-slate-400 text-xs">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
                    <span>No sensitive compliance or churn risk queries detected.</span>
                  </div>
                ) : (
                  recentLogs
                    .filter(l => l.policy_risk_flag || l.churn_risk_flag)
                    .map((item, idx) => (
                      <div 
                        key={idx}
                        className={`p-3.5 rounded-xl border space-y-2 ${
                          item.policy_risk_flag 
                            ? 'bg-rose-950/20 border-rose-500/30' 
                            : 'bg-amber-950/20 border-amber-500/30'
                        }`}
                      >
                        <div className="flex items-center justify-between text-xs">
                          <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                            item.policy_risk_flag 
                              ? 'bg-rose-500/20 text-rose-300' 
                              : 'bg-amber-500/20 text-amber-300'
                          }`}>
                            {item.policy_risk_flag ? 'POSH / POLICY COMPLIANCE' : 'CHURN / RETENTION RISK'}
                          </span>
                          <span className="text-slate-400 font-mono text-[10px]">
                            @{item.username} &bull; {item.created_at?.split('T')[0]}
                          </span>
                        </div>

                        <p className="text-xs font-semibold text-white">
                          "{item.query}"
                        </p>

                        <div className="text-[11px] text-slate-400 font-sans line-clamp-2">
                          {item.answer}
                        </div>
                      </div>
                    ))
                )}
              </div>

            </div>

          </div>

        </div>
      )}

      {/* =====================================================================
          TAB 5: DOCUMENT CATALOG & COMPANY INTELLIGENCE
          ===================================================================== */}
      {activeTab === 'catalog' && (
        <div className="space-y-8 animate-in fade-in duration-150">
          {/* Section 1: Source-Backed Company Knowledge Hub & Review-Before-Publish Workflow */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-[#0c101a] via-[#0f1424] to-[#12192e] border border-indigo-500/30 shadow-2xl space-y-6">
            
            {/* Header with Title, Stats & Action Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500/30 to-purple-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shadow-lg shadow-indigo-500/10">
                  <Building className="w-5 h-5 text-indigo-300" />
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h2 className="text-lg font-bold text-white font-['Outfit'] tracking-wide">
                      {trackedCompanies.find((c) => c.organization_id === selectedOrgId)?.company_name || companyForm?.company_name || 'Universal Enterprise Hub'}
                    </h2>
                    <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono font-bold">
                      Org: {selectedOrgId}
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Universal multi-company intelligence &bull; Multi-page crawler &bull; AI search tool &bull; Human-in-the-loop review &bull; Vector index sync
                  </p>
                </div>
              </div>

              {/* Company Switcher Dropdown & Actions */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                {/* Switcher Dropdown */}
                <div className="flex items-center gap-1.5 bg-black/60 border border-white/10 rounded-xl px-2.5 py-1 text-xs">
                  <span className="text-[10px] text-slate-400 font-bold uppercase font-mono">Company:</span>
                  <select
                    value={selectedOrgId}
                    onChange={(e) => {
                      const newOrg = e.target.value;
                      setSelectedOrgId(newOrg);
                      fetchFactCandidates(newOrg);
                      fetchApprovedFacts(newOrg);
                      fetchOutboxEvents(newOrg);
                    }}
                    className="bg-transparent text-white text-xs font-semibold focus:outline-none cursor-pointer pr-1"
                  >
                    {trackedCompanies.length === 0 ? (
                      <option value="default_org" className="bg-slate-900 text-white">Active Enterprise</option>
                    ) : (
                      trackedCompanies.map((c) => (
                        <option key={c.organization_id} value={c.organization_id} className="bg-slate-900 text-white">
                          {c.company_name || c.organization_id}
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <button
                  type="button"
                  onClick={() => setShowSearchToolDrawer(!showSearchToolDrawer)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                    showSearchToolDrawer
                      ? 'bg-cyan-600/30 border-cyan-500/50 text-cyan-200'
                      : 'bg-white/5 border-white/10 text-slate-300 hover:text-white'
                  }`}
                  title="Toggle Autonomous AI Search Tool to query missing corporate dimensions live"
                >
                  <Search className="w-3.5 h-3.5 text-cyan-400" />
                  <span>AI Search Tool</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleClearCompanyData(true)}
                  disabled={isClearingCompany}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/40 text-xs font-semibold text-rose-300 hover:text-white transition-all cursor-pointer disabled:opacity-50"
                  title="Purge previous company facts, candidate queue, and active profile"
                >
                  <Trash2 className={`w-3.5 h-3.5 text-rose-400 ${isClearingCompany ? 'animate-spin' : ''}`} />
                  <span>{isClearingCompany ? 'Clearing...' : 'Clear Company Data'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleProcessOutbox}
                  disabled={isProcessingOutbox}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-xs font-semibold text-emerald-300 hover:text-white transition-all cursor-pointer disabled:opacity-50"
                  title="Claim pending publication outbox events and synchronize with ChromaDB vector store safely"
                >
                  <Database className={`w-3.5 h-3.5 text-emerald-400 ${isProcessingOutbox ? 'animate-spin' : ''}`} />
                  <span>{isProcessingOutbox ? 'Publishing...' : 'Publish Outbox to Vector Store'}</span>
                </button>
              </div>
            </div>

            {/* AI Search Research Tool Drawer (Interactive Gap-Filler) */}
            {showSearchToolDrawer && (
              <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/30 space-y-3 animate-in fade-in duration-200">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-cyan-500/20 pb-2">
                  <div className="flex items-center gap-2 text-cyan-300 text-xs font-bold">
                    <Search className="w-4 h-4 text-cyan-400" />
                    <span>Autonomous AI Web Search Tool &bull; Fill Information Gaps Live</span>
                  </div>
                  <span className="text-[11px] text-cyan-200/80">
                    Queries search engines to resolve missing leadership, headcount, locations, or clients
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] font-bold text-slate-300">Dimension to Research:</span>
                  {[
                    { key: 'leadership', label: 'Leadership & CEO' },
                    { key: 'headquarters', label: 'Global HQ' },
                    { key: 'headcount', label: 'Workforce / Headcount' },
                    { key: 'plants', label: 'Manufacturing Plants' },
                    { key: 'clients', label: 'OEM Clients & Partners' },
                    { key: 'hubs', label: 'Spares & Logistics Hubs' },
                    { key: 'products', label: 'Products & Offerings' },
                    { key: 'financials', label: 'Revenue & Financials' },
                  ].map((dim) => (
                    <button
                      key={dim.key}
                      type="button"
                      onClick={() => setSearchToolFactType(dim.key)}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-mono font-semibold transition-all cursor-pointer ${
                        searchToolFactType === dim.key
                          ? 'bg-cyan-500/30 text-cyan-200 border border-cyan-400/50 shadow-sm'
                          : 'bg-black/40 text-slate-400 border border-white/5 hover:text-white'
                      }`}
                    >
                      {dim.label}
                    </button>
                  ))}

                  <button
                    type="button"
                    onClick={handleExecuteQuickGapSearch}
                    disabled={isSearchingGap}
                    className="ml-auto px-4 py-1.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer disabled:opacity-50 shadow-md shadow-cyan-600/20"
                  >
                    <Search className={`w-3.5 h-3.5 ${isSearchingGap ? 'animate-spin' : ''}`} />
                    <span>{isSearchingGap ? 'Searching Web...' : 'Search Live Web'}</span>
                  </button>
                </div>

                {/* Search Findings Results */}
                {searchToolResults.length > 0 && (
                  <div className="mt-3 space-y-2 border-t border-cyan-500/20 pt-3">
                    <span className="text-[10px] text-cyan-300 font-mono font-bold uppercase">
                      Live Search Findings ({searchToolResults.length} organic sources):
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      {searchToolResults.map((item, idx) => (
                        <div key={idx} className="p-2.5 rounded-lg bg-black/50 border border-white/5 space-y-1">
                          <div className="flex items-center justify-between text-[11px]">
                            <a
                              href={item.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-bold text-cyan-300 hover:underline flex items-center gap-1 truncate"
                            >
                              <span>{item.title}</span>
                              <ExternalLink className="w-3 h-3 shrink-0" />
                            </a>
                            <span className="text-[9px] font-mono text-slate-500">{item.source}</span>
                          </div>
                          <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-3">
                            "{item.snippet}"
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Universal Website Input Bar & Deep Crawl Action */}
            <div className="p-4 rounded-xl bg-[#090d17] border border-indigo-500/20 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Globe className="w-4 h-4 text-cyan-400" />
                  <span>Universal Autonomous Intelligence: Extract from Any Enterprise Domain</span>
                </label>
                <div className="flex items-center gap-2 text-xs">
                  <label className="flex items-center gap-1.5 text-[11px] text-slate-300 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={fillGapsWithSearch}
                      onChange={(e) => setFillGapsWithSearch(e.target.checked)}
                      className="rounded bg-black/60 border-white/20 text-indigo-500 focus:ring-0"
                    />
                    <span>Autonomous AI Search Gap-Filler</span>
                  </label>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
                <div className="relative flex-1">
                  <Globe className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="url"
                    placeholder="Enter any enterprise website URL (e.g. https://example.com)..."
                    value={companyUrlInput}
                    onChange={(e) => setCompanyUrlInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleExtractCompanyFromUrl();
                      }
                    }}
                    className="w-full pl-10 pr-10 py-2.5 bg-black/60 border border-white/10 rounded-xl text-white text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
                  />
                  {companyUrlInput && (
                    <button
                      type="button"
                      onClick={() => setCompanyUrlInput('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white text-xs cursor-pointer p-1"
                      title="Clear URL input"
                    >
                      &times;
                    </button>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => handleExtractCompanyFromUrl()}
                  disabled={isExtractingCompany || !companyUrlInput.trim()}
                  className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-600/30 cursor-pointer disabled:opacity-50 shrink-0"
                  title="Crawl official website and execute multi-query AI extraction for identity, locations, workforce, and clients"
                >
                  <Sparkles className={`w-4 h-4 text-cyan-200 ${isExtractingCompany ? 'animate-spin' : ''}`} />
                  <span>{isExtractingCompany ? 'Deep Crawling & AI Searching...' : 'Analyze & Extract Universal Intelligence'}</span>
                </button>
              </div>

              {/* Status / Alert Message */}
              {scrapeResultMsg && (
                <div className="p-3 rounded-lg bg-indigo-950/60 border border-indigo-500/40 text-xs text-indigo-200 font-mono flex items-center justify-between animate-in fade-in duration-200">
                  <div className="flex items-center gap-2">
                    <RotateCw className={`w-3.5 h-3.5 text-cyan-400 ${isExtractingCompany || isProcessingOutbox ? 'animate-spin' : ''}`} />
                    <span>{scrapeResultMsg}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setScrapeResultMsg('')}
                    className="text-slate-400 hover:text-white text-xs cursor-pointer ml-2"
                  >
                    &times;
                  </button>
                </div>
              )}
            </div>

            {/* Sub-Navigation Tabs: Candidate Review Queue vs Approved Grounding vs Outbox vs Manual Form */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setCompanyHubSubTab('candidates')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    companyHubSubTab === 'candidates'
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Candidate Review Queue</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-black/40 text-[10px] font-mono">
                    {factCandidates.length}
                  </span>
                  {factCandidates.some((c) => c.validation_status === 'conflicting') && (
                    <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" title="Conflicting facts require reconciliation" />
                  )}
                </button>

                <button
                  type="button"
                  onClick={() => setCompanyHubSubTab('approved')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    companyHubSubTab === 'approved'
                      ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/30'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  <Award className="w-3.5 h-3.5" />
                  <span>Approved Knowledge (Active RAG Truth)</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-black/40 text-[10px] font-mono">
                    {approvedFacts.length}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setCompanyHubSubTab('outbox')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    companyHubSubTab === 'outbox'
                      ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/30'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  <Database className="w-3.5 h-3.5" />
                  <span>Publication Outbox &amp; Vector Index</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-black/40 text-[10px] font-mono">
                    {outboxEvents.length}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setCompanyHubSubTab('edit_profile')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    companyHubSubTab === 'edit_profile'
                      ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                      : 'bg-white/5 text-slate-300 hover:bg-white/10'
                  }`}
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>Manual Form</span>
                </button>
              </div>

              <span className="text-[11px] text-slate-400 italic">
                {companyHubSubTab === 'candidates' && 'Review each extracted fact and citation individually before publication'}
                {companyHubSubTab === 'approved' && 'Only approved facts are active in PostgreSQL and serve the RAG assistant'}
                {companyHubSubTab === 'outbox' && 'Transactional outbox prevents desynchronization between PostgreSQL and ChromaDB'}
                {companyHubSubTab === 'edit_profile' && 'Direct field-by-field manual editing'}
              </span>
            </div>

            {/* =================================================================
                SUB-TAB 1: CANDIDATE REVIEW QUEUE
                ================================================================= */}
            {companyHubSubTab === 'candidates' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                {/* Section Filter Pills */}
                <div className="flex flex-wrap items-center gap-1.5 pb-1">
                  {[
                    { key: 'all', label: 'All Sections' },
                    { key: 'identity', label: '1. Identity & Leadership' },
                    { key: 'workforce', label: '2. Workforce & Headcount' },
                    { key: 'locations', label: '3. Locations & Plants' },
                    { key: 'clients', label: '4. Clients & OEMs' },
                    { key: 'hubs', label: '5. Logistics Hubs' },
                    { key: 'products', label: '6. Products & Solutions' },
                    { key: 'overview', label: '7. Markets & Overview' },
                    { key: 'innovation', label: '8. Technology & R&D' },
                  ].map((filter) => (
                    <button
                      key={filter.key}
                      type="button"
                      onClick={() => setCandidateSectionFilter(filter.key)}
                      className={`px-3 py-1 rounded-lg text-xs font-medium transition-all cursor-pointer ${
                        candidateSectionFilter === filter.key
                          ? 'bg-indigo-500/30 text-indigo-200 border border-indigo-500/50'
                          : 'bg-black/30 text-slate-400 hover:text-white border border-white/5'
                      }`}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>

                {/* Candidate Cards Grid */}
                <div className="grid grid-cols-1 gap-3.5">
                  {factCandidates
                    .filter((c) => candidateSectionFilter === 'all' || c.section_key === candidateSectionFilter)
                    .map((cand) => {
                      const isConflicting = cand.validation_status === 'conflicting';
                      const isApproved = cand.review_status === 'approved';
                      const isEditing = editingCandidateId === cand.id;
                      const evidenceItem = cand.evidence && cand.evidence.length > 0 ? cand.evidence[0] : null;

                      return (
                        <div
                          key={cand.id}
                          className={`p-4 rounded-xl border transition-all ${
                            isConflicting
                              ? 'bg-amber-950/20 border-amber-500/40 shadow-lg shadow-amber-950/20'
                              : isApproved
                              ? 'bg-black/30 border-emerald-500/30'
                              : 'bg-black/40 border-white/10 hover:border-indigo-500/30'
                          }`}
                        >
                          {/* Card Top Row: Meta Tags & Statuses */}
                          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2.5">
                            <div className="flex items-center gap-2">
                              <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                {cand.section_key}
                              </span>
                              <span className="text-xs font-bold text-white font-mono">
                                {cand.fact_key}
                              </span>
                              <span className="px-2 py-0.5 rounded font-mono text-[10px] bg-white/5 text-slate-400 border border-white/10">
                                Scope: {cand.scope_key}
                              </span>
                            </div>

                            <div className="flex items-center gap-2">
                              {/* Validation Status Badge */}
                              {cand.validation_status === 'valid' && (
                                <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-mono text-[10px] font-bold flex items-center gap-1">
                                  <Check className="w-3 h-3 text-emerald-400" />
                                  <span>Verified Fact</span>
                                </span>
                              )}
                              {cand.validation_status === 'conflicting' && (
                                <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/50 font-mono text-[10px] font-bold flex items-center gap-1 animate-pulse">
                                  <AlertTriangle className="w-3 h-3 text-amber-400" />
                                  <span>Conflict / Needs Reconciliation</span>
                                </span>
                              )}
                              {cand.validation_status === 'needs_review' && (
                                <span className="px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-mono text-[10px] font-bold flex items-center gap-1">
                                  <Clock className="w-3 h-3 text-cyan-400" />
                                  <span>Pending Review</span>
                                </span>
                              )}

                              {/* Review Status Badge */}
                              <span className={`px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold uppercase ${
                                isApproved
                                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                  : cand.review_status === 'needs_changes'
                                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                  : cand.review_status === 'rejected'
                                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                  : 'bg-white/10 text-slate-300 border border-white/10'
                              }`}>
                                {cand.review_status}
                              </span>
                            </div>
                          </div>

                          {/* Conflicting Source Alert Banner */}
                          {isConflicting && (
                            <div className="mt-3 p-3 rounded-xl bg-amber-950/40 border border-amber-500/50 text-xs text-amber-200 space-y-1">
                              <div className="flex items-center gap-2 font-bold text-amber-300">
                                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                                <span>Conflicting Source Claims Detected &bull; Reconciliation Required</span>
                              </div>
                              <p className="text-[11px] text-amber-200/90 leading-relaxed pl-6">
                                {cand.conflict_note || cand.validation_notes || 'Conflicting source claims detected across ingested pages. Review candidate value and reconcile evidence context before publishing.'}
                              </p>
                            </div>
                          )}

                          {/* Proposed Value Display / Inline Editor */}
                          <div className="mt-3 space-y-1.5">
                            <div className="flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                              <span>Candidate Proposed Value</span>
                              {!isEditing && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingCandidateId(cand.id);
                                    setEditingCandidateValue(
                                      typeof cand.proposed_value === 'object'
                                        ? JSON.stringify(cand.proposed_value, null, 2)
                                        : String(cand.proposed_value)
                                    );
                                  }}
                                  className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 text-[11px] font-mono cursor-pointer"
                                >
                                  <Edit3 className="w-3 h-3" />
                                  <span>Edit Value</span>
                                </button>
                              )}
                            </div>

                            {isEditing ? (
                              <div className="space-y-2">
                                <textarea
                                  rows={4}
                                  value={editingCandidateValue}
                                  onChange={(e) => setEditingCandidateValue(e.target.value)}
                                  className="w-full px-3 py-2 bg-black/70 border border-indigo-500/50 rounded-xl text-xs font-mono text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                                />
                                <div className="flex items-center gap-2 justify-end">
                                  <button
                                    type="button"
                                    onClick={() => setEditingCandidateId(null)}
                                    className="px-3 py-1 rounded-lg bg-white/10 hover:bg-white/20 text-xs text-slate-300 cursor-pointer"
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleSaveCandidateEdit(cand.id)}
                                    className="px-3 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-bold text-white cursor-pointer shadow-md shadow-indigo-600/30"
                                  >
                                    Save Edits
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <div className="p-3 rounded-xl bg-black/40 border border-white/5 text-xs text-slate-200 font-sans">
                                {typeof cand.proposed_value === 'object' && cand.proposed_value !== null ? (
                                  Array.isArray(cand.proposed_value) ? (
                                    <div className="flex flex-wrap gap-1.5">
                                      {cand.proposed_value.map((item, idx) => (
                                        <span
                                          key={idx}
                                          className="px-2.5 py-1 rounded-lg bg-white/5 border border-white/10 text-white font-mono text-[11px]"
                                        >
                                          {typeof item === 'object' ? `${item.facility || item.city || item.name} (${item.country || item.type || ''})` : String(item)}
                                        </span>
                                      ))}
                                    </div>
                                  ) : (
                                    <pre className="text-[11px] font-mono text-cyan-200 overflow-x-auto whitespace-pre-wrap">
                                      {JSON.stringify(cand.proposed_value, null, 2)}
                                    </pre>
                                  )
                                ) : (
                                  <span className="font-semibold text-white">{String(cand.proposed_value)}</span>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Exact Source Evidence Citation */}
                          {evidenceItem && (
                            <div className="mt-3 p-3 rounded-xl bg-white/[0.02] border-l-2 border-l-indigo-500 border border-white/5 space-y-1 text-xs">
                              <div className="flex items-center justify-between text-[11px]">
                                <span className="font-bold text-indigo-300 font-mono flex items-center gap-1">
                                  <span>Citation:</span>
                                  <span className="text-white font-sans">{evidenceItem.section_heading || 'Official Website Excerpt'}</span>
                                </span>
                                {evidenceItem.source_url && (
                                  <a
                                    href={evidenceItem.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-cyan-400 hover:text-cyan-300 font-mono text-[10px] flex items-center gap-1 underline underline-offset-2"
                                  >
                                    <span>{evidenceItem.source_url.replace('https://', '')}</span>
                                    <ExternalLink className="w-3 h-3" />
                                  </a>
                                )}
                              </div>
                              <p className="text-[11px] text-slate-300 italic leading-relaxed font-sans">
                                "{evidenceItem.evidence_text}"
                              </p>
                            </div>
                          )}

                          {/* Review Action Footer */}
                          <div className="mt-3.5 pt-2.5 border-t border-white/5 flex flex-wrap items-center justify-between gap-3">
                            <div className="text-[10px] text-slate-500 font-mono">
                              {cand.reviewed_by ? (
                                <span>Reviewed by @{cand.reviewed_by} &bull; {cand.reviewed_at?.split('T')[0]}</span>
                              ) : (
                                <span>Awaiting human review decision &bull; Confidence: {Math.round((cand.extraction_confidence || 1) * 100)}%</span>
                              )}
                            </div>

                            <div className="flex items-center gap-2">
                              {!isApproved ? (
                                <>
                                  {isConflicting && (
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setReconcilingCandidate(cand);
                                        setReconciledValueInput(
                                          typeof cand.proposed_value === 'object'
                                            ? JSON.stringify(cand.proposed_value, null, 2)
                                            : String(cand.proposed_value)
                                        );
                                        setReconciledReasonInput(
                                          cand.fact_key === 'regional_headcount'
                                            ? 'Reconciled India headcount conflict: Recorded 1,592 as audited plant personnel with 1,700+ narrative context.'
                                            : 'Reconciled conflicting source claims with verified reporting context.'
                                        );
                                      }}
                                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/40 text-amber-200 text-xs font-bold cursor-pointer transition-all shadow-md shadow-amber-950/20"
                                    >
                                      <GitMerge className="w-3.5 h-3.5 text-amber-400" />
                                      <span>Reconcile Claims</span>
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => handleReviewCandidate(cand.id, 'rejected', null, 'Rejected by admin during candidate review')}
                                    className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 border border-rose-500/30 text-rose-300 text-xs font-semibold cursor-pointer transition-all"
                                  >
                                    Reject
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleReviewCandidate(cand.id, 'needs_changes', null, 'Reconciliation or additional evidence required')}
                                    className="px-3 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 border border-amber-500/30 text-amber-300 text-xs font-semibold cursor-pointer transition-all"
                                  >
                                    Flag for Reconciliation
                                  </button>
                                  <button
                                    type="button"
                                    onClick={() => handleReviewCandidate(cand.id, 'approved')}
                                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-md shadow-emerald-600/20 cursor-pointer transition-all"
                                  >
                                    <Check className="w-3.5 h-3.5" />
                                    <span>Approve &amp; Enqueue Outbox</span>
                                  </button>
                                </>
                              ) : (
                                <div className="flex items-center gap-2">
                                  <span className="text-[11px] text-emerald-400 font-mono flex items-center gap-1">
                                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                    <span>Active in Grounded Knowledge</span>
                                  </span>
                                  <button
                                    type="button"
                                    onClick={() => handleReviewCandidate(cand.id, 'needs_changes', null, 'Revocation for re-review')}
                                    className="px-2.5 py-1 rounded bg-white/5 hover:bg-white/10 text-[10px] text-slate-400 hover:text-white cursor-pointer"
                                  >
                                    Revoke / Re-evaluate
                                  </button>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                </div>

                {/* Conflict Reconciliation Modal */}
                {reconcilingCandidate && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
                    <div className="w-full max-w-2xl bg-[#0f1424] border border-amber-500/40 rounded-2xl p-6 shadow-2xl space-y-5 text-white">
                      <div className="flex items-center justify-between border-b border-white/10 pb-3">
                        <div className="flex items-center gap-2.5">
                          <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30">
                            <GitMerge className="w-5 h-5" />
                          </div>
                          <div>
                            <h3 className="text-sm font-bold text-white font-['Outfit']">
                              Reconcile Conflicting Source Claims
                            </h3>
                            <p className="text-[11px] text-slate-400 font-mono">
                              Field: {reconcilingCandidate.section_key} &gt; {reconcilingCandidate.fact_key} ({reconcilingCandidate.scope_key})
                            </p>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setReconcilingCandidate(null)}
                          className="text-slate-400 hover:text-white text-lg cursor-pointer"
                        >
                          &times;
                        </button>
                      </div>

                      {/* Conflicting Claims Side-by-Side Comparison */}
                      <div className="space-y-2">
                        <label className="text-[11px] font-bold text-amber-300 uppercase tracking-wider">
                          Extracted Candidate &amp; Supporting Evidence
                        </label>
                        <div className="p-3.5 rounded-xl bg-black/50 border border-amber-500/20 space-y-2 text-xs">
                          <div className="flex items-center justify-between text-[10px] text-amber-400 font-bold font-mono uppercase">
                            <span>Candidate Dimension: {reconcilingCandidate.section_key} &bull; {reconcilingCandidate.fact_key}</span>
                            <span className="px-1.5 py-0.5 rounded bg-amber-500/20">{reconcilingCandidate.validation_status}</span>
                          </div>
                          <div>
                            <span className="text-slate-400 text-[11px] block font-mono">Proposed Value:</span>
                            <pre className="text-xs text-white font-mono bg-black/60 p-2 rounded-lg mt-1 overflow-x-auto whitespace-pre-wrap">
                              {typeof reconcilingCandidate.proposed_value === 'object'
                                ? JSON.stringify(reconcilingCandidate.proposed_value, null, 2)
                                : String(reconcilingCandidate.proposed_value)}
                            </pre>
                          </div>
                          {reconcilingCandidate.evidence && reconcilingCandidate.evidence.length > 0 && (
                            <div className="space-y-1 pt-1">
                              <span className="text-slate-400 text-[11px] block font-mono">Source Citations:</span>
                              {reconcilingCandidate.evidence.map((ev, evIdx) => (
                                <div key={evIdx} className="text-[11px] text-slate-300 bg-white/5 p-2 rounded-lg italic">
                                  "{ev.evidence_text}"
                                  {ev.source_url && (
                                    <div className="text-[10px] text-indigo-400 font-mono mt-0.5">{ev.source_url}</div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Editable Reconciled Value */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center justify-between">
                          <span>Reconciled Value to Approve &amp; Publish</span>
                          <span className="text-slate-500 font-mono text-[10px]">JSON or plain text</span>
                        </label>
                        <textarea
                          rows={4}
                          value={reconciledValueInput}
                          onChange={(e) => setReconciledValueInput(e.target.value)}
                          className="w-full px-3.5 py-2.5 bg-black/70 border border-white/10 rounded-xl text-xs font-mono text-cyan-200 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500"
                        />
                      </div>

                      {/* Audit Justification Note */}
                      <div className="space-y-1.5">
                        <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                          Reviewer Audit Justification Note
                        </label>
                        <input
                          type="text"
                          value={reconciledReasonInput}
                          onChange={(e) => setReconciledReasonInput(e.target.value)}
                          placeholder="Explain the reconciliation rationale for immutable audit trail..."
                          className="w-full px-3.5 py-2 bg-black/70 border border-white/10 rounded-xl text-xs text-white focus:outline-none focus:border-indigo-500"
                        />
                      </div>

                      {/* Modal Actions */}
                      <div className="flex items-center justify-end gap-2.5 pt-3 border-t border-white/10">
                        <button
                          type="button"
                          onClick={() => setReconcilingCandidate(null)}
                          className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-xs text-slate-300 font-semibold cursor-pointer"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={async () => {
                            let parsed = reconciledValueInput;
                            try {
                              parsed = JSON.parse(reconciledValueInput);
                            } catch (_) {}
                            await handleReviewCandidate(
                              reconcilingCandidate.id,
                              'approved',
                              parsed,
                              reconciledReasonInput || 'Reconciled conflicting source claims.'
                            );
                            setReconcilingCandidate(null);
                          }}
                          className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 cursor-pointer transition-all"
                        >
                          <Check className="w-4 h-4" />
                          <span>Approve &amp; Enqueue to Outbox</span>
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* =================================================================
                SUB-TAB 2: APPROVED KNOWLEDGE GROUNDING (ACTIVE POSTGRESQL TRUTH)
                ================================================================= */}
            {companyHubSubTab === 'approved' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 text-emerald-300 font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    <span>Current Active PostgreSQL Company Facts ({approvedFacts.length} verified records)</span>
                  </div>
                  <span className="text-slate-400 text-[11px]">
                    Only approved, active facts feed the RAG assistant with high retrieval priority
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {approvedFacts.map((fact) => (
                    <div
                      key={fact.id}
                      className="p-4 rounded-xl bg-black/40 border border-emerald-500/20 space-y-2 hover:border-emerald-500/40 transition-all text-xs"
                    >
                      <div className="flex items-center justify-between border-b border-white/5 pb-2">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded font-mono text-[10px] font-bold uppercase bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                            {fact.section_key}
                          </span>
                          <span className="font-bold text-white font-mono">{fact.fact_key}</span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-400">
                          v{fact.version} &bull; Scope: {fact.scope_key}
                        </span>
                      </div>

                      <div className="text-slate-200">
                        {typeof fact.approved_value === 'object' && fact.approved_value !== null ? (
                          Array.isArray(fact.approved_value) ? (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {fact.approved_value.map((val, idx) => (
                                <span
                                  key={idx}
                                  className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-slate-200 font-mono text-[11px]"
                                >
                                  {typeof val === 'object' ? `${val.facility || val.city || val.name} (${val.country || val.type || ''})` : String(val)}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <pre className="text-[11px] font-mono text-emerald-200 overflow-x-auto whitespace-pre-wrap">
                              {JSON.stringify(fact.approved_value, null, 2)}
                            </pre>
                          )
                        ) : (
                          <span className="font-bold text-white">{String(fact.approved_value)}</span>
                        )}
                      </div>

                      <div className="pt-2 flex items-center justify-between text-[10px] text-slate-500 font-mono border-t border-white/5">
                        <span>Approved by @{fact.approved_by || 'admin'}</span>
                        <span>{fact.approved_at?.split('T')[0]}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* =================================================================
                SUB-TAB 3: PUBLICATION OUTBOX & VECTOR SYNC
                ================================================================= */}
            {companyHubSubTab === 'outbox' && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-500/30 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-cyan-300 font-bold">
                      <Database className="w-4 h-4 text-cyan-400" />
                      <span>Transactional Publication Outbox ({outboxEvents.length} events)</span>
                    </div>
                    <button
                      type="button"
                      onClick={handleProcessOutbox}
                      disabled={isProcessingOutbox}
                      className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs cursor-pointer shadow-md shadow-cyan-600/30 flex items-center gap-1.5 disabled:opacity-50"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${isProcessingOutbox ? 'animate-spin' : ''}`} />
                      <span>{isProcessingOutbox ? 'Syncing...' : 'Process Pending Events'}</span>
                    </button>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
                    PostgreSQL and the ChromaDB vector index do not share a single distributed transaction. The outbox pattern commits the approved fact and its indexing job in the same PostgreSQL transaction. A worker then processes each outbox event idempotently, generating vector embeddings and updating ChromaDB.
                  </p>
                </div>

                {/* Outbox Events Table */}
                <div className="overflow-x-auto rounded-xl border border-white/10 bg-black/40">
                  <table className="w-full text-left text-xs font-mono">
                    <thead className="bg-white/5 border-b border-white/10 text-slate-400 text-[10px] uppercase tracking-wider">
                      <tr>
                        <th className="py-2.5 px-3">Entity Type</th>
                        <th className="py-2.5 px-3">Entity ID</th>
                        <th className="py-2.5 px-3">Version</th>
                        <th className="py-2.5 px-3">Operation</th>
                        <th className="py-2.5 px-3">Status</th>
                        <th className="py-2.5 px-3">Attempts</th>
                        <th className="py-2.5 px-3">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {outboxEvents.map((evt) => (
                        <tr key={evt.id} className="hover:bg-white/[0.02] text-slate-300">
                          <td className="py-2.5 px-3 font-semibold text-white">{evt.entity_type}</td>
                          <td className="py-2.5 px-3 text-cyan-300">{evt.entity_id.slice(0, 12)}...</td>
                          <td className="py-2.5 px-3">v{evt.entity_version}</td>
                          <td className="py-2.5 px-3 uppercase text-[10px]">{evt.operation}</td>
                          <td className="py-2.5 px-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              evt.status === 'completed'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : evt.status === 'processing'
                                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 animate-pulse'
                                : evt.status === 'failed'
                                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            }`}>
                              {evt.status}
                            </span>
                          </td>
                          <td className="py-2.5 px-3">{evt.attempts}</td>
                          <td className="py-2.5 px-3 text-slate-500 text-[10px]">{evt.created_at?.split('.')[0]?.replace('T', ' ')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* =================================================================
                SUB-TAB 4: MANUAL FORM (LEGACY PROFILE EDIT)
                ================================================================= */}
            {companyHubSubTab === 'edit_profile' && (
              <div className="space-y-6 pt-1 animate-in fade-in duration-150">
                <div className="flex items-center justify-between border-b border-white/5 pb-2">
                  <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                    <Edit3 className="w-4 h-4 text-purple-400" />
                    <span>Direct Profile Editing &amp; Vector Embed</span>
                  </div>
                  <span className="text-[11px] text-slate-400 italic">
                    Manually adjust corporate fields and re-embed all 5 profile grounding chunks
                  </span>
                </div>

                {/* Section A: Legal Identity & Leadership */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-4">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Briefcase className="w-3.5 h-3.5 text-indigo-400" />
                    <span>1. Company Legal Identity &amp; Leadership</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
                    <div>
                      <label className="block text-slate-400 font-semibold mb-1">Company Legal Name</label>
                      <input
                        type="text"
                        value={companyForm.company_name || ''}
                        onChange={(e) => setCompanyForm({ ...companyForm, company_name: e.target.value })}
                        placeholder="e.g. Acme Corporation"
                        className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 font-semibold mb-1">Parent MNC / Group</label>
                      <input
                        type="text"
                        value={companyForm.group_name || ''}
                        onChange={(e) => setCompanyForm({ ...companyForm, group_name: e.target.value })}
                        placeholder="e.g. Acme Group"
                        className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 font-semibold mb-1">Industry Sector</label>
                      <input
                        type="text"
                        value={companyForm.industry || ''}
                        onChange={(e) => setCompanyForm({ ...companyForm, industry: e.target.value })}
                        placeholder="e.g. Automotive, Industrial Automation, Clean Tech"
                        className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div>
                      <label className="block text-slate-400 font-semibold mb-1">Founded Year</label>
                      <input
                        type="text"
                        value={companyForm.founded_year || ''}
                        onChange={(e) => setCompanyForm({ ...companyForm, founded_year: e.target.value })}
                        placeholder="e.g. 1945"
                        className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500 font-mono"
                      />
                    </div>
                    <div className="sm:col-span-2">
                      <label className="block text-slate-400 font-semibold mb-1">Executive Leadership</label>
                      <input
                        type="text"
                        value={companyForm.ceo || ''}
                        onChange={(e) => setCompanyForm({ ...companyForm, ceo: e.target.value })}
                        placeholder="e.g. Natarajan Chandrasekaran (Chairman), Roland Busch (CEO)"
                        className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div className="sm:col-span-2 lg:col-span-3">
                      <label className="block text-slate-400 font-semibold mb-1">Corporate Overview &amp; Description</label>
                      <textarea
                        rows={2}
                        value={companyForm.description || ''}
                        onChange={(e) => setCompanyForm({ ...companyForm, description: e.target.value })}
                        placeholder="Comprehensive overview of company operations..."
                        className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500 resize-none"
                      />
                    </div>
                  </div>
                </div>

                {/* Section B: Workforce */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-cyan-400" />
                    <span>2. Workforce &amp; Headcount</span>
                  </div>
                  <input
                    type="text"
                    value={companyForm.employee_details || ''}
                    onChange={(e) => setCompanyForm({ ...companyForm, employee_details: e.target.value })}
                    placeholder="e.g. 3,795 employees globally (2025 company profile); India: 1,700+ narrative / 1,592 facility stat"
                    className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white text-xs font-sans focus:outline-none focus:border-cyan-500"
                  />
                </div>

                {/* Section C: Locations & Plants */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                      <span>3. All Company Locations &amp; 8 Global Manufacturing Plants ({companyForm.locations?.length || 0})</span>
                    </div>
                    <span className="text-[11px] text-slate-400">City, state, country, facility type</span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-56 overflow-y-auto pr-1">
                    {companyForm.locations && companyForm.locations.length > 0 ? (
                      companyForm.locations.map((loc, idx) => {
                        const isObj = typeof loc === 'object' && loc !== null;
                        const city = isObj ? (loc.city || loc.facility) : loc;
                        const state = isObj ? loc.state : '';
                        const country = isObj ? (loc.country || 'Italy') : '';
                        const type = isObj ? (loc.type || loc.role || 'Manufacturing Plant') : 'Facility';
                        const address = isObj ? loc.address : '';

                        return (
                          <div
                            key={idx}
                            className="flex items-start justify-between p-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-emerald-500/30 transition-all text-xs"
                          >
                            <div className="space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                                <span className="text-white font-bold">{city}</span>
                                {state && <span className="text-slate-400">, {state}</span>}
                                {country && <span className="text-slate-500 font-mono text-[10px]">({country})</span>}
                                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/25 font-medium">
                                  {type}
                                </span>
                              </div>
                              {address && <p className="text-[11px] text-slate-400 pl-4 font-sans">{address}</p>}
                            </div>
                            <button
                              type="button"
                              onClick={() => handleDeleteLocationItem(idx)}
                              className="text-slate-500 hover:text-rose-400 transition-colors cursor-pointer p-1 shrink-0 ml-2"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        );
                      })
                    ) : (
                      <div className="col-span-2 text-xs text-slate-500 italic p-3 text-center">No locations listed.</div>
                    )}
                  </div>

                  {/* Add Location Sub-Form */}
                  <div className="p-3 rounded-xl bg-black/50 border border-white/10 space-y-2.5">
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
                      <input
                        type="text"
                        placeholder="City (e.g. Campodarsego, Rovigo, Pune)"
                        value={newLocationInput.city}
                        onChange={(e) => setNewLocationInput({ ...newLocationInput, city: e.target.value })}
                        className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white font-sans"
                      />
                      <input
                        type="text"
                        placeholder="State / Region (e.g. Padua, Veneto)"
                        value={newLocationInput.state}
                        onChange={(e) => setNewLocationInput({ ...newLocationInput, state: e.target.value })}
                        className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white font-sans"
                      />
                      <input
                        type="text"
                        placeholder="Country (e.g. Italy, India, China)"
                        value={newLocationInput.country}
                        onChange={(e) => setNewLocationInput({ ...newLocationInput, country: e.target.value })}
                        className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white font-sans"
                      />
                      <input
                        type="text"
                        placeholder="Type (e.g. Global HQ, SIAP Plant)"
                        value={newLocationInput.type}
                        onChange={(e) => setNewLocationInput({ ...newLocationInput, type: e.target.value })}
                        className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white font-sans"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        placeholder="Full Address / Industrial Zone..."
                        value={newLocationInput.address}
                        onChange={(e) => setNewLocationInput({ ...newLocationInput, address: e.target.value })}
                        className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs font-sans"
                      />
                      <button
                        type="button"
                        onClick={handleAddLocationItem}
                        className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1.5 shrink-0"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add Location</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* Section D: Commercial Clients */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Award className="w-3.5 h-3.5 text-amber-400" />
                      <span>4. Commercial Clients &amp; OEM Partners ({companyForm.clients?.length || 0})</span>
                    </div>
                    <span className="text-[10px] text-amber-300 font-mono">Verified OEM Clients &amp; Partners</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {(companyForm.clients || []).map((client, cIdx) => (
                      <span key={cIdx} className="px-3 py-1 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 font-mono text-[11px] flex items-center gap-1.5">
                        <span>{client}</span>
                        <button type="button" onClick={() => handleDeleteClientItem(cIdx)} className="text-amber-400/60 hover:text-rose-400 cursor-pointer">&times;</button>
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      placeholder="Add Client / Partner name..."
                      value={newClientInput}
                      onChange={(e) => setNewClientInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddClientItem(); } }}
                      className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs font-mono"
                    />
                    <button type="button" onClick={handleAddClientItem} className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1 shrink-0">
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add</span>
                    </button>
                  </div>
                </div>

                {/* Section E: Logistics Hubs */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-indigo-400" />
                      <span>5. Regional Logistics &amp; Spares Hubs ({companyForm.hubs?.length || 0})</span>
                    </div>
                    <span className="text-[11px] text-slate-400">Driveservice in Poggiofiorito, Chieti, Italy</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {(companyForm.hubs || []).map((hub, hIdx) => (
                      <span key={hIdx} className="px-3 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 font-mono text-[11px] flex items-center gap-1.5">
                        <span>{hub}</span>
                        <button type="button" onClick={() => handleDeleteHubItem(hIdx)} className="text-indigo-400/60 hover:text-rose-400 cursor-pointer">&times;</button>
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      placeholder="Add logistics hub (e.g. Driveservice, Poggiofiorito, Chieti, Italy)..."
                      value={newHubInput}
                      onChange={(e) => setNewHubInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddHubItem(); } }}
                      className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs font-mono"
                    />
                    <button type="button" onClick={handleAddHubItem} className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1 shrink-0">
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Hub</span>
                    </button>
                  </div>
                </div>

                {/* Section F: Products & Mechanical Solutions (7 Categories) */}
                <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                      <Zap className="w-3.5 h-3.5 text-cyan-400" />
                      <span>6. Products &amp; Mechanical Solutions ({companyForm.products?.length || 0})</span>
                    </div>
                    <span className="text-[11px] text-slate-400">7 complete official categories</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {(companyForm.products || []).map((prod, pIdx) => (
                      <span key={pIdx} className="px-3 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 font-mono text-[11px] flex items-center gap-1.5">
                        <span>{prod}</span>
                        <button type="button" onClick={() => handleDeleteProductItem(pIdx)} className="text-cyan-400/60 hover:text-rose-400 cursor-pointer">&times;</button>
                      </span>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      placeholder="Add product category (e.g. Axles and transaxles, Specialized tractors, e-mobility)..."
                      value={newProductInput}
                      onChange={(e) => setNewProductInput(e.target.value)}
                      onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddProductItem(); } }}
                      className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs font-mono"
                    />
                    <button type="button" onClick={handleAddProductItem} className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-semibold text-xs cursor-pointer flex items-center gap-1 shrink-0">
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Product</span>
                    </button>
                  </div>
                </div>

                {/* Save Banner */}
                <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 via-black/40 to-indigo-950/40 border border-emerald-500/30 flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-0.5">
                    <div className="text-xs font-bold text-white flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span>Save Changes to PostgreSQL &amp; Vector Index</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Synchronizes modified fields into company_profiles and updates ChromaDB vector chunks.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleSaveAndEmbedCompanyProfile}
                    disabled={isApprovingProfile}
                    className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 cursor-pointer disabled:opacity-50 transition-all"
                  >
                    <Save className={`w-4 h-4 ${isApprovingProfile ? 'animate-spin' : ''}`} />
                    <span>{isApprovingProfile ? 'Saving & Embedding...' : 'Save & Embed Grounding Profile'}</span>
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Document Upload & Auto-Classification Zone (Directly Under Company Info) */}
          <div className="p-6 rounded-2xl bg-[#0f1422] border border-white/10 shadow-xl space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-md">
                  <Upload className="w-5 h-5 text-cyan-300" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white font-['Outfit'] flex items-center gap-2">
                    <span>Document Upload &amp; Auto-Classification</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-mono font-bold">
                      PDF, Markdown, TXT
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Upload employee policies, handbooks, SOPs, or guides. Auto-classifies category, extracts text, chunks, and indexes into PostgreSQL &amp; Vector Store.
                  </p>
                </div>
              </div>
            </div>

            {/* Document Title Input & Dynamic Fallback Feedback */}
            <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-2">
              <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
                Document Title (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Employee Code of Conduct 2026 (Leave empty to use PDF filename as title)..."
                value={docUploadTitle}
                onChange={(e) => setDocUploadTitle(e.target.value)}
                className="w-full px-3.5 py-2.5 bg-black/60 border border-white/10 rounded-xl text-white text-xs font-sans placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-medium"
              />
              <div className="text-[11px] font-mono flex items-center gap-1.5 pt-0.5">
                {docUploadTitle.trim() ? (
                  <span className="text-emerald-400 flex items-center gap-1">
                    <Check className="w-3.5 h-3.5" />
                    Title will be set to: <strong className="text-white">"{docUploadTitle.trim()}"</strong>
                  </span>
                ) : selectedUploadFile ? (
                  <span className="text-cyan-400 flex items-center gap-1">
                    <FileText className="w-3.5 h-3.5" />
                    Title not specified: Will automatically use filename <strong className="text-white">"{selectedUploadFile.name}"</strong> as title as it is.
                  </span>
                ) : (
                  <span className="text-slate-400 italic">
                    ℹ️ If title is not specified, it will automatically take the PDF or document filename as title as it is.
                  </span>
                )}
              </div>
            </div>

            {/* Upload Feedback Alert */}
            {uploadFeedback && (
              <div className={`p-4 rounded-xl border text-xs flex items-center justify-between animate-in fade-in duration-200 ${
                uploadFeedback.type === 'success' 
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300' 
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              }`}>
                <div className="flex items-center gap-2">
                  {uploadFeedback.type === 'success' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  )}
                  <span>{uploadFeedback.message}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setUploadFeedback(null)}
                  className="text-slate-400 hover:text-white text-xs font-bold cursor-pointer ml-3"
                >
                  &times;
                </button>
              </div>
            )}

            {/* Drag & Drop Area / Selected File Preview */}
            <div
              onClick={() => !isUploadingDoc && fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragActive(false);
                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                  setSelectedUploadFile(e.dataTransfer.files[0]);
                }
              }}
              className={`p-6 rounded-2xl border-2 border-dashed transition-all flex flex-col items-center justify-center text-center space-y-3 cursor-pointer select-none ${
                dragActive
                  ? 'border-cyan-500 bg-cyan-500/10'
                  : selectedUploadFile
                  ? 'border-emerald-500/50 bg-emerald-500/[0.04]'
                  : 'border-white/10 hover:border-cyan-500/40 bg-white/[0.01] hover:bg-white/[0.02]'
              }`}
            >
              <div className="w-12 h-12 rounded-2xl bg-cyan-600/20 text-cyan-400 flex items-center justify-center border border-cyan-500/30 shadow-md pointer-events-none">
                {isUploadingDoc ? (
                  <RotateCw className="w-6 h-6 animate-spin text-cyan-400" />
                ) : (
                  <FileText className="w-6 h-6 text-cyan-400" />
                )}
              </div>

              {isUploadingDoc ? (
                <div className="space-y-1 pointer-events-none">
                  <div className="text-sm font-semibold text-white">Analyzing, Classifying &amp; Embedding Document...</div>
                  <p className="text-xs text-slate-400">
                    Running DocumentClassifier, computing dense vector embeddings, and indexing into PostgreSQL &amp; ChromaDB.
                  </p>
                </div>
              ) : selectedUploadFile ? (
                <div className="space-y-1.5">
                  <div className="text-sm font-bold text-white flex items-center justify-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>File Selected: <span className="text-emerald-300 font-mono">{selectedUploadFile.name}</span></span>
                  </div>
                  <p className="text-xs text-slate-400 font-mono">
                    Size: {(selectedUploadFile.size / 1024).toFixed(1)} KB • Click to choose a different file or click Upload below
                  </p>
                </div>
              ) : (
                <div className="space-y-1 pointer-events-none">
                  <div className="text-sm font-semibold text-white">
                    Drag and drop your document here, or <span className="text-cyan-400 underline">browse files</span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Supported formats: PDF (.pdf), Markdown (.md), Plain Text (.txt)
                  </p>
                </div>
              )}

              <input
                ref={fileInputRef}
                type="file"
                disabled={isUploadingDoc}
                accept=".pdf,.md,.markdown,.txt"
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    setSelectedUploadFile(e.target.files[0]);
                  }
                }}
                className="hidden"
              />
            </div>

            {/* Upload Button */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-slate-400">
                {selectedUploadFile ? (
                  <span>Ready to ingest: <strong className="text-white">{selectedUploadFile.name}</strong></span>
                ) : (
                  <span>Select a document above to enable ingestion</span>
                )}
              </span>

              <button
                type="button"
                onClick={() => handleUploadDocument()}
                disabled={isUploadingDoc || !selectedUploadFile}
                className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 disabled:opacity-40 text-white text-xs font-bold transition-all shadow-md shadow-cyan-600/25 cursor-pointer"
              >
                <Upload className={`w-4 h-4 ${isUploadingDoc ? 'animate-spin' : ''}`} />
                <span>{isUploadingDoc ? 'Ingesting & Indexing...' : 'Upload & Auto-Classify Document'}</span>
              </button>
            </div>
          </div>

          {/* Section 3: Classification Breakdown Summary Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
            <div className="p-4 rounded-xl bg-[#0f1422] border border-white/10">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Total Files</div>
              <div className="text-2xl font-bold text-white font-mono mt-1">
                {catalogData?.summary?.total_documents ?? 0}
              </div>
              <div className="text-[10px] text-slate-400 mt-1 flex items-center gap-1 font-mono">
                <span className="text-emerald-400 font-semibold">{catalogData?.summary?.embedded_documents ?? 0}</span> embedded · 
                <span className="text-amber-400 font-semibold">{catalogData?.summary?.pending_documents ?? 0}</span> pending
              </div>
            </div>

            <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/30">
              <div className="text-[11px] font-semibold text-indigo-300 uppercase">Policies</div>
              <div className="text-2xl font-bold text-indigo-400 font-mono mt-1">
                {catalogData?.summary?.policies ?? 0}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30">
              <div className="text-[11px] font-semibold text-cyan-300 uppercase">Codes</div>
              <div className="text-2xl font-bold text-cyan-400 font-mono mt-1">
                {catalogData?.summary?.codes ?? 0}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
              <div className="text-[11px] font-semibold text-purple-300 uppercase">Programmes</div>
              <div className="text-2xl font-bold text-purple-400 font-mono mt-1">
                {catalogData?.summary?.programmes ?? 0}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
              <div className="text-[11px] font-semibold text-emerald-300 uppercase">Governance</div>
              <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">
                {catalogData?.summary?.governance ?? 0}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
              <div className="text-[11px] font-semibold text-amber-300 uppercase">Manuals &amp; Guides</div>
              <div className="text-2xl font-bold text-amber-400 font-mono mt-1">
                {catalogData?.summary?.manuals ?? 0}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
              <div className="text-[11px] font-semibold text-blue-300 uppercase flex items-center gap-1">
                <Database className="w-3 h-3 text-blue-400" />
                <span>Vector Chunks</span>
              </div>
              <div className="text-2xl font-bold text-blue-400 font-mono mt-1">
                {catalogData?.summary?.total_chunks ?? 0}
              </div>
            </div>
          </div>

          {/* Section 4: Filter Bar, Search, and Storage Sync & Batch Embed Actions */}
          <div className="p-4 rounded-2xl bg-[#0f1422] border border-white/10 flex flex-wrap items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 flex items-center gap-1.5 mr-2">
                <Filter className="w-3.5 h-3.5 text-indigo-400" />
                <span>Filter:</span>
              </span>
              {[
                { id: 'all', label: 'All Documents' },
                { id: 'policy', label: 'Policies' },
                { id: 'code', label: 'Codes' },
                { id: 'programme', label: 'Programmes' },
                { id: 'governance', label: 'Governance' },
                { id: 'manual', label: 'Manuals' },
              ].map((f) => (
                <button
                  key={f.id}
                  onClick={() => setCatalogFilter(f.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    catalogFilter === f.id
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'bg-white/5 text-slate-400 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>

            <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
              {/* Sync with Disk button */}
              <button
                type="button"
                onClick={handleSyncWithDisk}
                disabled={isSyncingDisk}
                title="Scan data/raw directory, purge deleted files from ChromaDB & DB, and detect new files"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] border border-white/10 text-xs font-semibold text-slate-200 transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isSyncingDisk ? 'animate-spin' : ''}`} />
                <span>{isSyncingDisk ? 'Syncing...' : 'Sync with Disk'}</span>
              </button>

              {/* Embed All Pending button */}
              {(catalogData?.summary?.pending_documents ?? 0) > 0 && (
                <button
                  type="button"
                  onClick={handleEmbedAllPending}
                  disabled={isEmbeddingAll}
                  title="Ingest, chunk, and embed all pending documents into ChromaDB"
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-600 to-indigo-600 hover:from-amber-500 hover:to-indigo-500 text-xs font-semibold text-white shadow-sm transition-all cursor-pointer disabled:opacity-50"
                >
                  <Zap className={`w-3.5 h-3.5 text-amber-200 ${isEmbeddingAll ? 'animate-spin' : ''}`} />
                  <span>{isEmbeddingAll ? 'Embedding...' : `Embed All Pending (${catalogData?.summary?.pending_documents})`}</span>
                </button>
              )}

              <div className="relative w-full sm:w-60">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search titles or filenames..."
                  value={catalogSearch}
                  onChange={(e) => setCatalogSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 bg-white/[0.04] border border-white/10 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* Section 5: Document Inventory Table with Embed Status, Chunks & Actions */}
          <div className="rounded-2xl bg-[#0f1422] border border-white/10 overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 bg-white/[0.02] text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                    <th className="py-3.5 px-4">#</th>
                    <th className="py-3.5 px-4">Document Title</th>
                    <th className="py-3.5 px-4">Classification</th>
                    <th className="py-3.5 px-4">Business Category</th>
                    <th className="py-3.5 px-4">Governance Level</th>
                    <th className="py-3.5 px-4">Source Filename</th>
                    <th className="py-3.5 px-4">Size</th>
                    <th className="py-3.5 px-4">Vector Chunks / Status</th>
                    <th className="py-3.5 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 font-sans">
                  {catalogData?.documents
                    ?.filter((doc) => {
                      if (catalogFilter !== 'all' && doc.doc_type !== catalogFilter) return false;
                      if (!catalogSearch) return true;
                      const q = catalogSearch.toLowerCase();
                      return (
                        (doc.title && doc.title.toLowerCase().includes(q)) ||
                        (doc.source && doc.source.toLowerCase().includes(q)) ||
                        (doc.category && doc.category.toLowerCase().includes(q))
                      );
                    })
                    .map((doc, idx) => (
                      <tr key={doc.id || idx} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3 px-4 font-mono text-slate-500">{idx + 1}</td>
                        <td className="py-3 px-4 font-semibold text-white">
                          {doc.title}
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2.5 py-0.5 rounded-full font-semibold text-[10px] uppercase font-mono ${
                            doc.doc_type === 'policy'
                              ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                              : doc.doc_type === 'code'
                              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                              : doc.doc_type === 'programme'
                              ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                              : doc.doc_type === 'governance'
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                          }`}>
                            {doc.doc_type}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          {doc.category}
                        </td>
                        <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                          {doc.governance_level || 'Board Level'}
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-400 truncate max-w-xs">
                          {doc.source}
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-400 whitespace-nowrap">
                          {formatFileSize(doc.file_size_bytes)}
                        </td>
                        <td className="py-3 px-4 whitespace-nowrap">
                          {doc.is_embedded || (doc.chunk_count && doc.chunk_count > 0) ? (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              <span>Embedded ({doc.chunk_count} {doc.chunk_count === 1 ? 'chunk' : 'chunks'})</span>
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <AlertTriangle className="w-3 h-3 text-amber-400" />
                              <span>Pending Indexing (0 chunks)</span>
                            </span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right whitespace-nowrap">
                          <div className="flex items-center justify-end gap-1.5">
                            {(!doc.is_embedded || doc.chunk_count === 0) && (
                              <button
                                type="button"
                                onClick={() => handleEmbedSingle(doc.source)}
                                disabled={embeddingSources[doc.source]}
                                title={`Embed ${doc.source} into ChromaDB`}
                                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600/50 border border-indigo-500/40 text-indigo-200 text-[11px] font-medium transition-colors cursor-pointer disabled:opacity-50"
                              >
                                <Zap className={`w-3 h-3 text-amber-400 ${embeddingSources[doc.source] ? 'animate-spin' : ''}`} />
                                <span>{embeddingSources[doc.source] ? 'Embedding...' : 'Embed'}</span>
                              </button>
                            )}
                            <button
                              type="button"
                              onClick={() => handleDeleteDocument(doc.source)}
                              title={`Delete ${doc.source} from disk and vector index`}
                              className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
