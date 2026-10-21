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
  Check
} from 'lucide-react';

export default function DashboardPage({ onRerunQuery, apiBaseUrl = '', currentUser, onOpenAuthModal }) {
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
  const [companyUrlInput, setCompanyUrlInput] = useState('https://www.carraro.com');
  const [isEditingCompany, setIsEditingCompany] = useState(false);
  const [isReviewMode, setIsReviewMode] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [isApprovingProfile, setIsApprovingProfile] = useState(false);
  const [isReindexingEmbeddings, setIsReindexingEmbeddings] = useState(false);
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
    company_name: 'Carraro India Limited',
    group_name: 'Carraro Group',
    industry: 'Automotive & Mechanical Transmission Systems',
    description: 'Leading global manufacturer of mechanical transmission systems, axles, and drive systems for agricultural tractors and construction machinery.',
    ceo: 'Mr. Balaji Gopalan (Managing Director)',
    founded_year: '1997',
    employee_details: '500+ employees (India Plant: 450+ engineers & workforce; Global Carraro: 3,500+)',
    clients: ['John Deere', 'CNH Industrial', 'Mahindra & Mahindra', 'Caterpillar', 'Escorts Kubota', 'Case IH', '100+ OEM Clients'],
    hubs: ['Pune Central Spares Hub', 'Padua Global Distribution Center'],
    products: ['Agricultural Tractor Transmissions', 'Construction Equipment Axles', 'Drive Systems', 'Precision Gears', 'Electric Powertrains'],
    locations: [
      { city: 'Pune', state: 'Maharashtra', country: 'India', type: 'Manufacturing Plant', address: 'B-85, MIDC, Ranjangaon, Pune - 412209' },
      { city: 'Padua', state: 'Veneto', country: 'Italy', type: 'Global Headquarters', address: 'Via Olmo, 37, 35011 Campodarsego, Padua' }
    ],
    domains_urls: ['https://www.carraro.com'],
  });

  // Document Upload States (with Title input & Filename fallback)
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [docUploadTitle, setDocUploadTitle] = useState('');
  const [selectedUploadFile, setSelectedUploadFile] = useState(null);
  const fileInputRef = useRef(null);

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
            company_name: prof.company_name || 'Carraro India Limited',
            group_name: prof.group_name || 'Carraro Group',
            industry: prof.industry || 'Automotive & Mechanical Transmission Systems',
            description: prof.description || '',
            ceo: prof.ceo || '',
            founded_year: meta.founded_year || prof.founded_year || '1997',
            employee_details: prof.employee_details || '500+ employees (India Plant: 450+ engineers & workforce; Global: 3,500+)',
            clients: clientsList.length > 0 ? clientsList : ['John Deere', 'CNH Industrial', 'Mahindra & Mahindra', '100+ OEM Clients'],
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
    } catch (err) {
      console.error('Failed to fetch dashboard telemetry:', err);
    } finally {
      setLoading(false);
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
      alert('Please enter a company website URL (e.g. https://www.carraro.com)');
      return;
    }
    setIsExtractingCompany(true);
    setIsScrapingCompany(true);
    setScrapeResultMsg('🌐 Crawling official website, exploring subpages, & running multi-query AI extraction for locations, clients, and workforce...');
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/company/scrape-preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: target }),
      });
      const data = await res.json();
      if (res.ok && (data.status === 'preview_ready' || data.preview)) {
        const preview = data.preview;
        setPreviewData(preview);
        const meta = preview.metadata_json || {};
        
        const locs = Array.isArray(preview.locations) ? preview.locations : [];
        const clientsArr = Array.isArray(meta.clients) ? meta.clients : (Array.isArray(preview.clients) ? preview.clients : []);
        const hubsArr = Array.isArray(meta.hubs) ? meta.hubs : (Array.isArray(preview.hubs) ? preview.hubs : []);
        const prodsArr = Array.isArray(preview.products) ? preview.products : [];
        const urlsArr = Array.isArray(preview.domains_urls) ? preview.domains_urls : [target];

        setCompanyForm({
          company_name: preview.company_name || 'Carraro India Limited',
          group_name: preview.group_name || 'Carraro Group',
          industry: preview.industry || 'Automotive & Mechanical Transmission Systems',
          description: preview.description || '',
          ceo: preview.ceo || '',
          founded_year: meta.founded_year || preview.founded_year || '1997',
          employee_details: preview.employee_details || '500+ employees',
          clients: clientsArr.length > 0 ? clientsArr : ['John Deere', 'CNH Industrial', 'Mahindra & Mahindra', '100+ OEM Clients'],
          hubs: hubsArr,
          products: prodsArr,
          locations: locs,
          domains_urls: urlsArr,
        });

        setIsReviewMode(true);
        setIsEditingCompany(true);
        setScrapeResultMsg(`✅ AI Multi-Query extraction complete from ${data.crawled_urls?.length || 1} pages! Check and validate the details below before saving.`);
      } else {
        setScrapeResultMsg(`⚠️ ${data.message || 'Scrape completed with warnings.'}`);
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

  const handleDeleteDocument = async (source) => {
    if (!confirm(`Are you sure you want to remove "${source}" from PostgreSQL and vector index?`)) return;
    try {
      const res = await fetch(`${apiBaseUrl}/api/v1/catalog/${encodeURIComponent(source)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        const resCatalog = await fetch(`${apiBaseUrl}/api/v1/catalog`);
        if (resCatalog.ok) setCatalogData(await resCatalog.json());
      }
    } catch (err) {
      console.error('Failed to delete document:', err);
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
          setUserChatHistory(json.history || []);
        }
      } catch (err) {
        console.error('Failed to load user chat history:', err);
      } finally {
        setHistoryLoading(false);
      }
    };
    fetchUserHistory();
  }, [selectedUser]);

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
                  <h3 className="text-sm font-bold text-white font-['Outfit'] flex items-center gap-2">
                    <span>Query Intelligence &amp; Semantic Cache Layer</span>
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold">
                      ACTIVE
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Shorthand rewriting, scope safety gating, and zero-token cached inference (&lt;10ms)
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

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
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
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* User Directory Column */}
            <div className="lg:col-span-1 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <Users className="w-4 h-4 text-indigo-400" />
                  <span>Registered Users ({userList.length})</span>
                </h3>
                <span className="text-xs text-slate-400 font-mono">PostgreSQL</span>
              </div>

              <div className="space-y-2">
                {userList.map((u) => {
                  const isSelected = selectedUser === u.username;
                  return (
                    <div
                      key={u.id}
                      onClick={() => setSelectedUser(u.username)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                        isSelected
                          ? 'bg-indigo-950/40 border-indigo-500 shadow-md shadow-indigo-950/50'
                          : 'bg-[#0b0f19] border-white/10 hover:border-white/20 hover:bg-white/[0.02]'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className={`w-9 h-9 rounded-full flex items-center justify-center font-bold text-sm ${
                          u.role === 'admin'
                            ? 'bg-amber-500 text-black'
                            : 'bg-indigo-600 text-white'
                        }`}>
                          {u.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="text-sm font-bold text-white">{u.username}</span>
                            <span className={`text-[9px] px-1.5 py-0.2 rounded font-mono font-bold uppercase ${
                              u.role === 'admin'
                                ? 'bg-amber-500/20 text-amber-300'
                                : 'bg-cyan-500/20 text-cyan-300'
                            }`}>
                              {u.role}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 font-mono">{u.email}</span>
                        </div>
                      </div>

                      <div className="text-right">
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

            {/* Individual User Chat History Column */}
            <div className="lg:col-span-2 space-y-4">
              
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                    Full Chat Audit for <span className="text-indigo-400 font-mono">@{selectedUser}</span>
                  </h3>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {userChatHistory.length} total recorded turns
                </span>
              </div>

              {historyLoading ? (
                <div className="p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
                  <RotateCw className="w-4 h-4 animate-spin text-indigo-400" />
                  <span>Loading chat history from PostgreSQL...</span>
                </div>
              ) : userChatHistory.length === 0 ? (
                <div className="p-12 rounded-2xl bg-[#0b0f19] border border-white/10 text-center space-y-2">
                  <p className="text-slate-300 text-sm font-semibold">No queries recorded yet for @{selectedUser}</p>
                  <p className="text-slate-400 text-xs">
                    Switch to this account in the Search page to ask questions and see their full provenance here.
                  </p>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Group messages by session_id to render multi-prompt conversational threads */}
                  {(() => {
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

                    const sessionThreads = Object.values(sessionMap);
                    sessionThreads.forEach((sess) => {
                      sess.turns.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
                      sess.firstQuery = sess.turns[0]?.query || 'Conversation';
                    });
                    sessionThreads.sort((a, b) => new Date(b.lastActivity) - new Date(a.lastActivity));

                    return sessionThreads.map((thread, tIdx) => (
                      <div 
                        key={thread.sessionId || tIdx}
                        className="rounded-2xl bg-[#0b0f19] border border-white/10 overflow-hidden shadow-xl hover:border-indigo-500/30 transition-all space-y-4"
                      >
                        {/* Conversation Session Header */}
                        <div className="px-5 py-3.5 bg-white/[0.02] border-b border-white/10 flex flex-wrap items-center justify-between gap-3">
                          <div className="space-y-0.5">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono font-bold">
                                Session: {thread.sessionId}
                              </span>
                              <span className="text-[10px] text-slate-400 font-mono">
                                {thread.lastActivity?.split('T')[0]} {thread.lastActivity?.split('T')[1]?.slice(0, 5)}
                              </span>
                              {thread.hasRisk && (
                                <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30 font-mono font-bold">
                                  RISK SIGNAL IN THREAD
                                </span>
                              )}
                            </div>
                            <h4 className="text-sm font-bold text-white flex items-center gap-2">
                              <MessageSquare className="w-4 h-4 text-cyan-400 shrink-0" />
                              <span className="truncate">"{thread.firstQuery}"</span>
                            </h4>
                          </div>

                          <div className="flex items-center gap-3 text-right text-xs font-mono">
                            <span className="px-2.5 py-1 rounded-lg bg-white/[0.04] text-slate-300 font-semibold">
                              💬 {thread.turns.length} {thread.turns.length === 1 ? 'Prompt' : 'Prompts'}
                            </span>
                            <span className="text-cyan-400 font-bold">
                              {thread.totalTokens.toLocaleString()} tokens
                            </span>
                          </div>
                        </div>

                        {/* Turn-by-turn prompts and responses in this session */}
                        <div className="p-5 space-y-5">
                          {thread.turns.map((item, turnIdx) => {
                            const isExpanded = expandedMessageId === item.id;
                            const chunks = item.chunks_sent || [];
                            const citations = item.citations || [];

                            return (
                              <div key={item.id} className="space-y-3 relative">
                                
                                {turnIdx > 0 && (
                                  <div className="w-full border-t border-white/5 my-4" />
                                )}

                                {/* Prompt Header & Number */}
                                <div className="flex items-center justify-between text-xs">
                                  <div className="flex items-center gap-2">
                                    <span className="w-5 h-5 rounded-full bg-white/10 text-white font-mono font-bold text-[10px] flex items-center justify-center">
                                      {turnIdx + 1}
                                    </span>
                                    <span className="text-slate-400 font-semibold">User Prompt:</span>
                                    <span className="text-[10px] text-slate-500 font-mono">{item.trace_id}</span>
                                  </div>

                                  <div className="text-right text-[11px] font-mono text-emerald-400">
                                    {item.total_latency_ms}ms &bull; {item.total_tokens} tokens
                                  </div>
                                </div>

                                {/* User Question Box */}
                                <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/30 text-white text-xs font-medium">
                                  {item.query}
                                </div>

                                {/* Assistant Generated Response */}
                                <div className="p-4 rounded-xl bg-black/40 border border-white/5 space-y-3 text-xs text-slate-300 font-sans leading-relaxed">
                                  <div className="text-slate-200">
                                    {item.answer}
                                  </div>

                                  {/* Citations & Chunks Inspection Toggle */}
                                  <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/5 text-xs">
                                    <div className="flex flex-wrap items-center gap-1.5 text-slate-400 text-[11px]">
                                      <span className="font-semibold text-slate-300">Citations:</span>
                                      {citations.length > 0 ? (
                                        citations.map((c, i) => (
                                          <span key={i} className="px-1.5 py-0.5 rounded bg-white/[0.05] text-[10px] text-cyan-300 font-mono">
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
                                      className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 text-xs font-semibold cursor-pointer"
                                    >
                                      <span>{isExpanded ? 'Hide' : 'Inspect'} Chunks ({chunks.length})</span>
                                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                                    </button>
                                  </div>

                                  {/* Collapsible Chunks Sent to LLM */}
                                  {isExpanded && (
                                    <div className="mt-3 p-3.5 rounded-xl bg-[#07090e] border border-white/10 space-y-2 animate-in fade-in duration-150">
                                      <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-1">
                                        Retrieved Chunks Context:
                                      </div>
                                      {chunks.length === 0 ? (
                                        <p className="text-xs text-slate-500 italic">No chunk data stored for this turn.</p>
                                      ) : (
                                        <div className="space-y-2">
                                          {chunks.map((chk, cIdx) => (
                                            <div key={cIdx} className="p-2.5 rounded-lg bg-white/[0.02] border border-white/5 space-y-1">
                                              <div className="flex items-center justify-between text-[11px] font-mono">
                                                <span className="text-indigo-400 font-semibold">
                                                  [{cIdx + 1}] {chk.source || 'doc'} {chk.page ? `(p.${chk.page})` : ''}
                                                </span>
                                                <span className="text-emerald-400">
                                                  Score: {chk.score ? `${Math.round(chk.score * 100)}%` : 'N/A'}
                                                </span>
                                              </div>
                                              <p className="text-[11px] text-slate-400 line-clamp-2 font-mono">
                                                {chk.text || 'No text snippet'}
                                              </p>
                                            </div>
                                          ))}
                                        </div>
                                      )}

                                      <div className="pt-2 border-t border-white/5 grid grid-cols-4 gap-2 text-[10px] font-mono text-center text-slate-400">
                                        <div>Embed: <span className="text-white">{item.embed_latency_ms}ms</span></div>
                                        <div>Search: <span className="text-white">{item.search_latency_ms}ms</span></div>
                                        <div>Rerank: <span className="text-white">{item.rerank_latency_ms}ms</span></div>
                                        <div>LLM: <span className="text-white">{item.generation_latency_ms}ms</span></div>
                                      </div>
                                    </div>
                                  )}
                                </div>

                              </div>
                            );
                          })}
                        </div>

                      </div>
                    ));
                  })()}
                </div>
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
          
          <div className="flex items-center justify-between border-b border-white/10 pb-4">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Search className="w-5 h-5 text-indigo-400" />
                <span>Distributed Request Tracing &amp; Retrieval Inspector</span>
              </h3>
              <p className="text-xs text-slate-400">
                Inspect every query hop: embedding inference, vector retrieval in ChromaDB, cross-encoder reranking, and generation.
              </p>
            </div>
            
            <button
              onClick={() => setRiskFilter(!riskFilter)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer ${
                riskFilter
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                  : 'bg-white/[0.04] text-slate-300 border-white/10 hover:bg-white/[0.08]'
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              <span>{riskFilter ? 'Showing Risk Only' : 'Filter Risk Signals'}</span>
            </button>
          </div>

          <div className="space-y-3">
            {recentLogs
              .filter((log) => !riskFilter || log.policy_risk_flag || log.churn_risk_flag)
              .map((log) => (
                <div 
                  key={log.id}
                  className="p-4 rounded-xl bg-[#0b0f19] border border-white/10 hover:border-indigo-500/30 transition-all space-y-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-mono text-indigo-300 font-semibold">{log.trace_id}</span>
                      <span className="text-slate-500">&bull;</span>
                      <span className="px-2 py-0.5 rounded bg-white/[0.06] font-mono text-slate-300 font-semibold">
                        @{log.username}
                      </span>
                      <span className="text-slate-500">&bull;</span>
                      <span className="text-slate-400 font-mono text-[11px]">{log.created_at}</span>
                    </div>

                    <div className="flex items-center gap-3 text-xs font-mono">
                      <span className="text-slate-400">In: {log.input_tokens}t</span>
                      <span className="text-slate-400">Out: {log.output_tokens}t</span>
                      <span className="text-emerald-400 font-bold">{log.total_latency_ms}ms</span>
                    </div>
                  </div>

                  <div className="text-sm font-semibold text-white">
                    {log.query}
                  </div>

                  <div className="p-3 rounded-lg bg-black/40 border border-white/5 text-xs text-slate-300 font-sans">
                    {log.answer}
                  </div>

                  {/* Latency Waterfall Bar */}
                  <div className="space-y-1">
                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                      <span>Latency Breakdown (Waterfall)</span>
                      <span>Total: {log.total_latency_ms}ms</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden flex">
                      <div 
                        title={`Embedding: ${log.embed_latency_ms}ms`}
                        style={{ width: `${Math.max((log.embed_latency_ms / (log.total_latency_ms || 1)) * 100, 5)}%` }}
                        className="bg-purple-500 h-full"
                      />
                      <div 
                        title={`Vector Search: ${log.search_latency_ms}ms`}
                        style={{ width: `${Math.max((log.search_latency_ms / (log.total_latency_ms || 1)) * 100, 5)}%` }}
                        className="bg-blue-500 h-full"
                      />
                      <div 
                        title={`Reranker: ${log.rerank_latency_ms}ms`}
                        style={{ width: `${Math.max((log.rerank_latency_ms / (log.total_latency_ms || 1)) * 100, 5)}%` }}
                        className="bg-cyan-500 h-full"
                      />
                      <div 
                        title={`LLM Generation: ${log.generation_latency_ms}ms`}
                        style={{ width: `${Math.max((log.generation_latency_ms / (log.total_latency_ms || 1)) * 100, 20)}%` }}
                        className="bg-emerald-500 h-full"
                      />
                    </div>
                    <div className="flex items-center gap-4 text-[10px] font-mono text-slate-400 pt-1">
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-purple-500" /> Embed: {log.embed_latency_ms}ms</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-blue-500" /> Search: {log.search_latency_ms}ms</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-cyan-500" /> Rerank: {log.rerank_latency_ms}ms</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded bg-emerald-500" /> LLM: {log.generation_latency_ms}ms</span>
                    </div>
                  </div>

                </div>
              ))}
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
          {/* Section 1: Company Info & Multi-Query AI Extractor (Corporate Knowledge Hub) */}
          <div className="p-6 rounded-2xl bg-gradient-to-br from-[#0c101a] via-[#0f1424] to-[#12192e] border border-indigo-500/30 shadow-2xl space-y-6">
            {/* Header with Title & Stats */}
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/10 pb-4">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-indigo-500/30 to-purple-500/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shadow-lg shadow-indigo-500/10">
                  <Building className="w-5 h-5 text-indigo-300" />
                </div>
                <div>
                  <div className="flex items-center gap-2.5">
                    <h2 className="text-lg font-bold text-white font-['Outfit'] tracking-wide">
                      {companyForm?.company_name || companyProfile?.company_name || 'Company Info & Knowledge Hub'}
                    </h2>
                    {(companyForm?.group_name || companyProfile?.group_name) && (
                      <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-mono font-bold">
                        {companyForm?.group_name || companyProfile?.group_name}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Multi-query AI extraction from corporate websites • Section-wise fact verification • Grounded PostgreSQL &amp; Vector Store
                  </p>
                </div>
              </div>

              {/* Status & Quick Stats Badges */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <div className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 font-mono text-[11px] flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{companyForm.locations?.length || 0} Locations</span>
                </div>
                <div className="px-3 py-1.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 font-mono text-[11px] flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-cyan-400" />
                  <span>500+ Workforce</span>
                </div>
                <div className="px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 font-mono text-[11px] flex items-center gap-1.5">
                  <Award className="w-3.5 h-3.5 text-amber-400" />
                  <span>{companyForm.clients?.length || 0} Clients (100+)</span>
                </div>
                <button
                  type="button"
                  onClick={handleReindexEmbeddings}
                  disabled={isReindexingEmbeddings}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-xs font-semibold text-indigo-300 hover:text-white transition-all cursor-pointer disabled:opacity-50"
                  title="Re-embed corporate profile facts directly into ChromaDB vector store"
                >
                  <Database className={`w-3.5 h-3.5 text-indigo-400 ${isReindexingEmbeddings ? 'animate-spin' : ''}`} />
                  <span>{isReindexingEmbeddings ? 'Embedding...' : 'Sync Vector Store'}</span>
                </button>
              </div>
            </div>

            {/* URL Input Bar & Multi-Query AI Extraction Button */}
            <div className="p-4 rounded-xl bg-[#090d17] border border-indigo-500/20 space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Globe className="w-4 h-4 text-cyan-400" />
                  <span>Corporate Website URL Input &amp; AI Multi-Query Extraction</span>
                </label>
                <span className="text-[11px] text-slate-400">
                  Crawls /locations, /plants, /about, /clients &amp; runs 3 specialized LLM queries
                </span>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2.5">
                <div className="relative flex-1">
                  <Globe className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="url"
                    placeholder="Enter company website URL (e.g. https://www.carraro.com)..."
                    value={companyUrlInput}
                    onChange={(e) => setCompanyUrlInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleExtractCompanyFromUrl();
                      }
                    }}
                    className="w-full pl-10 pr-4 py-2.5 bg-black/60 border border-white/10 rounded-xl text-white text-xs font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-all"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleExtractCompanyFromUrl()}
                  disabled={isExtractingCompany || !companyUrlInput.trim()}
                  className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white text-xs font-bold transition-all shadow-lg shadow-indigo-600/30 cursor-pointer disabled:opacity-50 shrink-0"
                  title="Crawl official website and execute multi-query AI extraction for identity, locations, workforce, and clients"
                >
                  <Sparkles className={`w-4 h-4 text-cyan-200 ${isExtractingCompany ? 'animate-spin' : ''}`} />
                  <span>{isExtractingCompany ? 'Crawling & AI Extracting...' : 'AI Extract Details'}</span>
                </button>
              </div>

              {/* Status / Alert Message */}
              {scrapeResultMsg && (
                <div className="p-3 rounded-lg bg-indigo-950/60 border border-indigo-500/40 text-xs text-indigo-200 font-mono flex items-center justify-between animate-in fade-in duration-200">
                  <div className="flex items-center gap-2">
                    <RotateCw className={`w-3.5 h-3.5 text-cyan-400 ${isExtractingCompany ? 'animate-spin' : ''}`} />
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

            {/* Section-Wise Corporate Fact Validation Form */}
            <div className="space-y-6 pt-1">
              <div className="flex items-center justify-between border-b border-white/5 pb-2">
                <div className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Validate &amp; Check Extracted Details Section-Wise</span>
                </div>
                <span className="text-[11px] text-slate-400 italic">
                  Review and edit before saving to PostgreSQL &amp; Vector Store
                </span>
              </div>

              {/* SECTION A: Company Identity & Overview */}
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
                      placeholder="e.g. Carraro India Limited"
                      className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Parent MNC / Group</label>
                    <input
                      type="text"
                      value={companyForm.group_name || ''}
                      onChange={(e) => setCompanyForm({ ...companyForm, group_name: e.target.value })}
                      placeholder="e.g. Carraro Group"
                      className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Industry Sector</label>
                    <input
                      type="text"
                      value={companyForm.industry || ''}
                      onChange={(e) => setCompanyForm({ ...companyForm, industry: e.target.value })}
                      placeholder="e.g. Automotive & Mechanical Transmission Systems"
                      className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 font-semibold mb-1">Founded Year</label>
                    <input
                      type="text"
                      value={companyForm.founded_year || ''}
                      onChange={(e) => setCompanyForm({ ...companyForm, founded_year: e.target.value })}
                      placeholder="e.g. 1997"
                      className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500 font-mono"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="block text-slate-400 font-semibold mb-1">Executive Leadership (MD / CEO / Directors)</label>
                    <input
                      type="text"
                      value={companyForm.ceo || ''}
                      onChange={(e) => setCompanyForm({ ...companyForm, ceo: e.target.value })}
                      placeholder="e.g. Mr. Balaji Gopalan (Managing Director)"
                      className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div className="sm:col-span-2 lg:col-span-3">
                    <label className="block text-slate-400 font-semibold mb-1">Corporate Overview &amp; Description</label>
                    <textarea
                      rows={2}
                      value={companyForm.description || ''}
                      onChange={(e) => setCompanyForm({ ...companyForm, description: e.target.value })}
                      placeholder="Comprehensive overview of company business operations and manufacturing scope..."
                      className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white font-sans focus:outline-none focus:border-indigo-500 resize-none"
                    />
                  </div>
                </div>
              </div>

              {/* SECTION B: Workforce & Headcount (500+ Employees) */}
              <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Users className="w-3.5 h-3.5 text-cyan-400" />
                    <span>2. Workforce &amp; Headcount (500+ Employees)</span>
                  </div>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-mono font-bold">
                    Headcount Metric
                  </span>
                </div>
                <div>
                  <input
                    type="text"
                    value={companyForm.employee_details || ''}
                    onChange={(e) => setCompanyForm({ ...companyForm, employee_details: e.target.value })}
                    placeholder="e.g. 500+ employees (India Plant: 450+ engineers & manufacturing staff; Global Carraro: 3,500+)"
                    className="w-full px-3 py-2 bg-black/50 border border-white/10 rounded-xl text-white text-xs font-sans focus:outline-none focus:border-cyan-500"
                  />
                  <p className="text-[11px] text-slate-500 mt-1">
                    Directly grounds queries such as "How many employees work at the company?" and "What is the staff count?".
                  </p>
                </div>
              </div>

              {/* SECTION C: All Company Locations & Manufacturing Plants */}
              <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                    <span>3. All Company Locations, Plants &amp; Offices ({companyForm.locations?.length || 0})</span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    City, state, country, facility type, and address
                  </span>
                </div>

                {/* Locations Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-56 overflow-y-auto pr-1">
                  {companyForm.locations && companyForm.locations.length > 0 ? (
                    companyForm.locations.map((loc, idx) => {
                      const isObj = typeof loc === 'object' && loc !== null;
                      const city = isObj ? loc.city : loc;
                      const state = isObj ? loc.state : '';
                      const country = isObj ? (loc.country || 'India') : '';
                      const type = isObj ? (loc.type || 'Manufacturing Plant') : 'Facility';
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
                            {address && (
                              <p className="text-[11px] text-slate-400 pl-4 leading-relaxed font-sans">
                                {address}
                              </p>
                            )}
                          </div>
                          <button
                            type="button"
                            onClick={() => handleDeleteLocationItem(idx)}
                            className="text-slate-500 hover:text-rose-400 transition-colors cursor-pointer p-1 shrink-0 ml-2"
                            title="Remove this location"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      );
                    })
                  ) : (
                    <div className="col-span-2 text-xs text-slate-500 italic p-3 text-center bg-white/[0.01] rounded-xl border border-white/5">
                      No locations listed yet. Add a location or plant below.
                    </div>
                  )}
                </div>

                {/* Add Location Sub-Form */}
                <div className="p-3 rounded-xl bg-black/50 border border-white/10 space-y-2.5">
                  <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Plus className="w-3 h-3 text-emerald-400" />
                    <span>Add New Plant / Office Location</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 text-xs">
                    <input
                      type="text"
                      placeholder="City (e.g. Pune, Ranjangaon)"
                      value={newLocationInput.city}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, city: e.target.value })}
                      className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-sans"
                    />
                    <input
                      type="text"
                      placeholder="State / Region (e.g. Maharashtra)"
                      value={newLocationInput.state}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, state: e.target.value })}
                      className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-sans"
                    />
                    <input
                      type="text"
                      placeholder="Country (e.g. India, Italy)"
                      value={newLocationInput.country}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, country: e.target.value })}
                      className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-sans"
                    />
                    <input
                      type="text"
                      placeholder="Type (e.g. Plant 1, HQ, R&D)"
                      value={newLocationInput.type}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, type: e.target.value })}
                      className="px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-sans"
                    />
                  </div>
                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                    <input
                      type="text"
                      placeholder="Full Address / Industrial Estate (e.g. B-85, MIDC, Ranjangaon, Pune - 412209)..."
                      value={newLocationInput.address}
                      onChange={(e) => setNewLocationInput({ ...newLocationInput, address: e.target.value })}
                      className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-sans"
                    />
                    <button
                      type="button"
                      onClick={handleAddLocationItem}
                      className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs cursor-pointer flex items-center justify-center gap-1.5 shrink-0 shadow-md shadow-emerald-600/20"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Location</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* SECTION D: Commercial Clients & OEM Partners (100+ Clients) */}
              <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Award className="w-3.5 h-3.5 text-amber-400" />
                    <span>4. Commercial Clients &amp; OEM Partners ({companyForm.clients?.length || 0})</span>
                  </div>
                  <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 font-mono font-bold">
                    100+ Commercial Clients
                  </span>
                </div>

                {/* Client Tags */}
                <div className="flex flex-wrap items-center gap-2">
                  {(companyForm.clients || []).map((client, cIdx) => (
                    <span
                      key={cIdx}
                      className="px-3 py-1 rounded-lg bg-amber-500/10 border border-amber-500/25 text-amber-300 font-mono text-[11px] font-semibold flex items-center gap-1.5"
                    >
                      <span>{client}</span>
                      <button
                        type="button"
                        onClick={() => handleDeleteClientItem(cIdx)}
                        className="text-amber-400/60 hover:text-rose-400 cursor-pointer ml-0.5"
                        title="Remove client"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>

                {/* Add Client Input */}
                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Add OEM Client (e.g. John Deere, CNH Industrial, Mahindra, Caterpillar, Escorts)..."
                    value={newClientInput}
                    onChange={(e) => setNewClientInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddClientItem();
                      }
                    }}
                    className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:border-amber-500 font-mono"
                  />
                  <button
                    type="button"
                    onClick={handleAddClientItem}
                    disabled={!newClientInput.trim()}
                    className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-40 text-white font-semibold text-xs cursor-pointer flex items-center gap-1 shrink-0"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Client</span>
                  </button>
                </div>
              </div>

              {/* SECTION E: Regional Logistics Hubs & Warehouses */}
              <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-indigo-400" />
                    <span>5. Regional Logistics &amp; Spares Hubs ({companyForm.hubs?.length || 0})</span>
                  </div>
                  <span className="text-[11px] text-slate-400">Parts distribution &amp; assembly centers</span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {(companyForm.hubs || []).map((hub, hIdx) => (
                    <span
                      key={hIdx}
                      className="px-3 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-indigo-300 font-mono text-[11px] font-semibold flex items-center gap-1.5"
                    >
                      <span>{hub}</span>
                      <button
                        type="button"
                        onClick={() => handleDeleteHubItem(hIdx)}
                        className="text-indigo-400/60 hover:text-rose-400 cursor-pointer ml-0.5"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Add logistics hub (e.g. Pune Central Spares Hub, Padua Global Center)..."
                    value={newHubInput}
                    onChange={(e) => setNewHubInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddHubItem();
                      }
                    }}
                    className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                  />
                  <button
                    type="button"
                    onClick={handleAddHubItem}
                    disabled={!newHubInput.trim()}
                    className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold text-xs cursor-pointer flex items-center gap-1 shrink-0"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Hub</span>
                  </button>
                </div>
              </div>

              {/* SECTION F: Precision Products & Engineering Solutions */}
              <div className="p-4 rounded-xl bg-black/30 border border-white/5 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Zap className="w-3.5 h-3.5 text-cyan-400" />
                    <span>6. Products &amp; Mechanical Solutions ({companyForm.products?.length || 0})</span>
                  </div>
                  <span className="text-[11px] text-slate-400">Manufactured mechanical assemblies</span>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {(companyForm.products || []).map((prod, pIdx) => (
                    <span
                      key={pIdx}
                      className="px-3 py-1 rounded-lg bg-cyan-500/10 border border-cyan-500/25 text-cyan-300 font-mono text-[11px] font-semibold flex items-center gap-1.5"
                    >
                      <span>{prod}</span>
                      <button
                        type="button"
                        onClick={() => handleDeleteProductItem(pIdx)}
                        className="text-cyan-400/60 hover:text-rose-400 cursor-pointer ml-0.5"
                      >
                        &times;
                      </button>
                    </span>
                  ))}
                </div>

                <div className="flex items-center gap-2 pt-1">
                  <input
                    type="text"
                    placeholder="Add product (e.g. Agricultural Axles, Transmission Systems, Drive Solutions)..."
                    value={newProductInput}
                    onChange={(e) => setNewProductInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddProductItem();
                      }
                    }}
                    className="flex-1 px-3 py-1.5 bg-black/60 border border-white/10 rounded-lg text-white text-xs placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono"
                  />
                  <button
                    type="button"
                    onClick={handleAddProductItem}
                    disabled={!newProductInput.trim()}
                    className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-white font-semibold text-xs cursor-pointer flex items-center gap-1 shrink-0"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    <span>Add Product</span>
                  </button>
                </div>
              </div>
            </div>

            {/* SAVE BUTTON BANNER */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 via-black/40 to-indigo-950/40 border border-emerald-500/30 flex flex-wrap items-center justify-between gap-4">
              <div className="space-y-0.5">
                <div className="text-xs font-bold text-white flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Validation Complete? Commit &amp; Embed Knowledge</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Stores verified facts in PostgreSQL (<code className="text-emerald-300 font-mono">company_profiles</code>) and re-indexes ChromaDB vectors so the AI can answer questions about all company locations, employees, and clients.
                </p>
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleSaveAndEmbedCompanyProfile}
                  disabled={isApprovingProfile}
                  className="flex items-center gap-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-500 hover:from-emerald-500 hover:to-teal-400 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 cursor-pointer disabled:opacity-50 transition-all"
                >
                  <Save className={`w-4 h-4 ${isApprovingProfile ? 'animate-spin' : ''}`} />
                  <span>{isApprovingProfile ? 'Saving & Embedding...' : 'Save & Embed Company Knowledge'}</span>
                </button>
              </div>
            </div>
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
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-4 rounded-xl bg-[#0f1422] border border-white/10">
              <div className="text-[11px] font-semibold text-slate-400 uppercase">Total Files</div>
              <div className="text-2xl font-bold text-white font-mono mt-1">
                {catalogData?.summary?.total_documents || 33}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-indigo-500/10 border border-indigo-500/30">
              <div className="text-[11px] font-semibold text-indigo-300 uppercase">Policies</div>
              <div className="text-2xl font-bold text-indigo-400 font-mono mt-1">
                {catalogData?.summary?.policies || 21}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30">
              <div className="text-[11px] font-semibold text-cyan-300 uppercase">Codes</div>
              <div className="text-2xl font-bold text-cyan-400 font-mono mt-1">
                {catalogData?.summary?.codes || 4}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
              <div className="text-[11px] font-semibold text-purple-300 uppercase">Programmes</div>
              <div className="text-2xl font-bold text-purple-400 font-mono mt-1">
                {catalogData?.summary?.programmes || 3}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30">
              <div className="text-[11px] font-semibold text-emerald-300 uppercase">Governance</div>
              <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">
                {catalogData?.summary?.governance || 1}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30">
              <div className="text-[11px] font-semibold text-amber-300 uppercase">Manuals &amp; Guides</div>
              <div className="text-2xl font-bold text-amber-400 font-mono mt-1">
                {catalogData?.summary?.manuals || 4}
              </div>
            </div>
          </div>

          {/* Section 4: Filter Bar & Search */}
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

            <div className="relative w-full sm:w-64">
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

          {/* Section 5: Document Inventory Table with Delete Action */}
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
                        <td className="py-3 px-4 text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteDocument(doc.source)}
                            title={`Delete ${doc.source}`}
                            className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors cursor-pointer"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
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
