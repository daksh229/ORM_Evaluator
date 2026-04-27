import React, { useState, useRef, useEffect } from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  Search, 
  Settings, 
  Upload, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  ChevronRight,
  MoreVertical,
  Download,
  Eye,
  Camera,
  Scan,
  Database
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { cn } from './lib/utils';
import { GLStyleSheetPreview } from './components/TemplatePreview';
import * as api from './services/api';
import { expandFiles } from './lib/pdfToImages';

// --- Types ---
interface Session {
  id: string;
  name: string;
  date: string;
  status: 'processing' | 'completed' | 'review_required';
  sheets: number;
  accuracy: number;
}

function metaToSession(meta: api.SessionMeta): Session {
  return {
    id: meta.id,
    name: meta.name,
    date: (meta.created_at || '').split('T')[0] || meta.created_at || '',
    status: meta.sheet_count === 0 ? 'processing' : 'completed',
    sheets: meta.sheet_count,
    accuracy: 0,
  };
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [isUploading, setIsUploading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [sessionSheets, setSessionSheets] = useState<api.SheetResult[]>([]);
  const [uploadProgress, setUploadProgress] = useState<{ done: number; total: number } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const cameraInputRef = useRef<HTMLInputElement>(null);

  const loadSessions = async () => {
    try {
      const metas = await api.listSessions();
      setSessions(metas.map(metaToSession));
    } catch (e) {
      console.error('Failed to load sessions:', e);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (!selectedSessionId) {
      setSessionSheets([]);
      return;
    }
    api.getSession(selectedSessionId)
      .then(s => setSessionSheets(s.sheets))
      .catch(e => console.error('Failed to load session:', e));
  }, [selectedSessionId]);

  // Templates list + selection (Templates tab + Settings status).
  const [availableTemplates, setAvailableTemplates] = useState<string[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('AE_STANDARD');
  const [engineHealthy, setEngineHealthy] = useState<boolean>(false);

  useEffect(() => {
    api.listTemplates()
      .then(ts => {
        setAvailableTemplates(ts);
        setEngineHealthy(true);
        if (ts.length > 0 && !ts.includes(selectedTemplateId)) {
          setSelectedTemplateId(ts[0]);
        }
      })
      .catch(() => setEngineHealthy(false));
  }, []);

  const reviewCount = sessionSheets.reduce(
    (sum, s) => sum + s.process_result.boxes.filter(b => b.source === 'claude').length,
    0,
  );

  const handleOverride = async (
    sheetId: string,
    boxIndex: number,
    status: 'marked' | 'blank',
  ) => {
    if (!selectedSessionId) return;
    try {
      await api.overrideBox(selectedSessionId, sheetId, boxIndex, status);
      const session = await api.getSession(selectedSessionId);
      setSessionSheets(session.sheets);
    } catch (e) {
      console.error('Override failed:', e);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const rawFiles = Array.from(e.target.files || []);
    if (rawFiles.length === 0) return;
    setIsUploading(true);

    // Expand any PDFs into one PNG per page so the engine sees a flat list
    // of single-page images regardless of upload source (PDF / image / camera).
    let files: File[];
    try {
      files = await expandFiles(rawFiles);
    } catch (err) {
      console.error('Failed to expand PDFs:', err);
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (cameraInputRef.current) cameraInputRef.current.value = '';
      return;
    }
    if (files.length === 0) {
      setIsUploading(false);
      return;
    }
    setUploadProgress({ done: 0, total: files.length });
    try {
      const session = await api.createSession({
        name: `Batch ${new Date().toLocaleString()}`,
        template_id: 'AE_STANDARD',
        answer_key_id: 'AE_STANDARD_KEY',
      });
      for (let i = 0; i < files.length; i++) {
        try {
          await api.addScanToSession(session.id, files[i]);
        } catch (err) {
          console.error(`Failed to upload ${files[i].name}:`, err);
        }
        setUploadProgress({ done: i + 1, total: files.length });
      }
      setSelectedSessionId(session.id);
      await loadSessions();
      setActiveTab('export');
    } catch (err) {
      console.error('Upload failed:', err);
    } finally {
      setIsUploading(false);
      setUploadProgress(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (cameraInputRef.current) cameraInputRef.current.value = '';
    }
  };

  return (
    <div className="flex h-screen bg-[#E4E3E0] text-[#141414] font-sans selection:bg-[#141414] selection:text-[#E4E3E0]">
      {/* Sidebar */}
      <aside className="w-64 border-r border-[#141414] flex flex-col">
        <div className="p-6 border-bottom border-[#141414]">
          <div className="flex items-center gap-2">
            <Scan className="w-6 h-6" />
            <h1 className="font-serif italic font-bold text-xl tracking-tight">OMR Scanner</h1>
          </div>
          <p className="text-[10px] uppercase tracking-widest opacity-50 mt-1">GL-Style System v1.0</p>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          <NavItem 
            icon={<LayoutDashboard size={18} />} 
            label="Dashboard" 
            active={activeTab === 'dashboard'} 
            onClick={() => setActiveTab('dashboard')} 
          />
          <NavItem 
            icon={<FileText size={18} />} 
            label="Templates" 
            active={activeTab === 'templates'} 
            onClick={() => setActiveTab('templates')} 
          />
          <NavItem 
            icon={<AlertCircle size={18} />} 
            label="Review Queue" 
            active={activeTab === 'review'} 
            onClick={() => setActiveTab('review')} 
            badge={reviewCount}
          />
          <NavItem 
            icon={<Database size={18} />} 
            label="Data Export" 
            active={activeTab === 'export'} 
            onClick={() => setActiveTab('export')} 
          />
        </nav>

        <div className="p-4 border-t border-[#141414]">
          <NavItem 
            icon={<Settings size={18} />} 
            label="Settings" 
            active={activeTab === 'settings'} 
            onClick={() => setActiveTab('settings')} 
          />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <header className="h-16 border-b border-[#141414] flex items-center justify-between px-8 bg-white/50 backdrop-blur-sm sticky top-0 z-10">
          <div className="flex items-center gap-4">
            <h2 className="font-serif italic text-lg capitalize">{activeTab}</h2>
            <div className="h-4 w-[1px] bg-[#141414]/20" />
            <div className="flex items-center gap-2 text-[11px] opacity-50 uppercase tracking-wider">
              <Clock size={12} />
              Last Sync: 2 mins ago
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="bg-[#141414] text-[#E4E3E0] px-4 py-2 text-xs uppercase tracking-widest font-bold hover:bg-[#333] transition-colors flex items-center gap-2"
              title="Upload PDF or image files (multi-page PDFs are split into one image per page)"
            >
              <Upload size={14} />
              Upload
            </button>
            <button
              onClick={() => cameraInputRef.current?.click()}
              className="border border-[#141414] text-[#141414] px-4 py-2 text-xs uppercase tracking-widest font-bold hover:bg-[#141414] hover:text-[#E4E3E0] transition-colors flex items-center gap-2"
              title="Capture a sheet with the device camera (mobile / tablet)"
            >
              <Camera size={14} />
              Camera
            </button>
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              onChange={handleUpload}
              multiple
              accept=".pdf,image/*"
            />
            <input
              type="file"
              ref={cameraInputRef}
              className="hidden"
              onChange={handleUpload}
              accept="image/*"
              capture="environment"
            />
          </div>
        </header>

        <div className="p-8 max-w-6xl mx-auto">
          {/* Platform Note */}
          <div className="mb-8 p-4 border border-[#141414] bg-blue-50 text-[11px] leading-relaxed">
            <div className="flex items-center gap-2 font-bold uppercase tracking-widest mb-1">
              <AlertCircle size={14} className="text-blue-600" />
              Hybrid OCR + Claude Vision
            </div>
            Classical OpenCV handles ~95% of marks deterministically — fast, offline, and free.
            The remaining ambiguous cases (light marks, erasures, smudges) are escalated to <b>Claude Vision</b> for human-level judgment,
            then logged in the Review Queue for optional manual verification.
          </div>

          <AnimatePresence mode="wait">
            {activeTab === 'dashboard' && (
              <motion.div 
                key="dashboard"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-8"
              >
                {/* Stats Grid */}
                <div className="grid grid-cols-4 gap-4">
                  <StatCard label="Total Sheets" value="2,481" delta="+12%" />
                  <StatCard label="Avg Accuracy" value="99.2%" delta="+0.4%" />
                  <StatCard label="Pending Review" value="14" delta="-2" warning />
                  <StatCard label="System Load" value="12%" delta="Normal" />
                </div>

                {/* Upload Status */}
                {isUploading && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    className="border border-[#141414] p-6 bg-white"
                  >
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="animate-spin rounded-full h-4 w-4 border-2 border-[#141414] border-t-transparent" />
                        <span className="text-xs font-bold uppercase tracking-widest">
                          Processing Batch{uploadProgress ? ` (${uploadProgress.done}/${uploadProgress.total})` : '...'}
                        </span>
                      </div>
                      <span className="text-[10px] font-mono">
                        {uploadProgress
                          ? `${Math.round((uploadProgress.done / uploadProgress.total) * 100)}% Complete`
                          : 'Starting...'}
                      </span>
                    </div>
                    <div className="h-1 bg-[#E4E3E0] w-full">
                      <motion.div
                        className="h-full bg-[#141414]"
                        initial={{ width: 0 }}
                        animate={{
                          width: uploadProgress
                            ? `${(uploadProgress.done / uploadProgress.total) * 100}%`
                            : '5%',
                        }}
                      />
                    </div>
                    <div className="mt-4 grid grid-cols-3 gap-4 text-[10px] font-mono opacity-60">
                      <div>[OK] Deskewing scanned pages</div>
                      <div>[OK] Aligning fiducials</div>
                      <div>[AI] Classifying ambiguous marks via Claude</div>
                    </div>
                  </motion.div>
                )}

                {/* Recent Sessions Table */}
                <div className="border border-[#141414] bg-white overflow-hidden">
                  <div className="p-4 border-b border-[#141414] flex justify-between items-center bg-[#f9f9f9]">
                    <h3 className="font-serif italic text-sm">Recent Scanning Sessions</h3>
                    <button className="text-[10px] uppercase tracking-widest font-bold hover:underline">View All</button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="border-b border-[#141414] text-[10px] uppercase tracking-widest opacity-50">
                          <th className="p-4 font-normal">Session Name</th>
                          <th className="p-4 font-normal">Date</th>
                          <th className="p-4 font-normal">Status</th>
                          <th className="p-4 font-normal">Sheets</th>
                          <th className="p-4 font-normal text-right">Accuracy</th>
                          <th className="p-4 font-normal"></th>
                        </tr>
                      </thead>
                      <tbody>
                        {sessions.length === 0 && !isUploading && (
                          <tr>
                            <td colSpan={6} className="p-8 text-center text-[11px] uppercase tracking-widest opacity-50">
                              No scanning sessions yet — click "New Scan" to upload
                            </td>
                          </tr>
                        )}
                        {sessions.map((session) => (
                          <tr
                            key={session.id}
                            onClick={() => { setSelectedSessionId(session.id); setActiveTab('export'); }}
                            className="border-b border-[#141414]/10 hover:bg-[#141414] hover:text-[#E4E3E0] transition-colors cursor-pointer group"
                          >
                            <td className="p-4 text-xs font-bold">{session.name}</td>
                            <td className="p-4 text-[11px] font-mono opacity-70">{session.date}</td>
                            <td className="p-4">
                              <StatusBadge status={session.status} />
                            </td>
                            <td className="p-4 text-[11px] font-mono">{session.sheets}</td>
                            <td className="p-4 text-[11px] font-mono text-right">
                              {session.accuracy > 0 ? `${session.accuracy}%` : '—'}
                            </td>
                            <td className="p-4 text-right">
                              <button className="opacity-0 group-hover:opacity-100 transition-opacity">
                                <ChevronRight size={16} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </motion.div>
            )}

            {activeTab === 'templates' && (
              <motion.div
                key="templates"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                className="space-y-6"
              >
                <div className="flex justify-between items-end gap-4">
                  <div>
                    <h3 className="font-serif italic text-2xl">Templates</h3>
                    <p className="text-xs opacity-60 mt-1">
                      {availableTemplates.length === 0
                        ? 'No templates found — run python -m omr_engine.pdf.generate'
                        : `${availableTemplates.length} template${availableTemplates.length === 1 ? '' : 's'} available — pick one to download`}
                    </p>
                  </div>
                  <div className="flex gap-2 items-center">
                    <select
                      value={selectedTemplateId}
                      onChange={(e) => setSelectedTemplateId(e.target.value)}
                      className="border border-[#141414] px-3 py-2 text-[10px] uppercase font-bold bg-white"
                    >
                      {availableTemplates.length === 0 && (
                        <option value="">No templates</option>
                      )}
                      {availableTemplates.map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                    <a
                      href={selectedTemplateId && availableTemplates.includes(selectedTemplateId) ? api.templatePdfUrl(selectedTemplateId) : '#'}
                      onClick={(e) => {
                        if (!selectedTemplateId || !availableTemplates.includes(selectedTemplateId)) e.preventDefault();
                      }}
                      className={cn(
                        "bg-[#141414] text-white px-4 py-2 text-[10px] uppercase font-bold hover:bg-[#333] transition-colors flex items-center gap-2",
                        (!selectedTemplateId || !availableTemplates.includes(selectedTemplateId)) && "opacity-30 cursor-not-allowed pointer-events-none"
                      )}
                    >
                      <Download size={14} />
                      Download PDF
                    </a>
                  </div>
                </div>

                <div className="border border-[#141414] bg-white p-6">
                  <GLStyleSheetPreview templateId={selectedTemplateId} />
                </div>

                <div className="border border-[#141414] bg-blue-50 p-4 text-[11px] leading-relaxed">
                  <p className="font-bold uppercase tracking-widest mb-1">To edit a template's layout</p>
                  <p className="opacity-70">
                    Templates are defined as Python builders in <code className="font-mono bg-white px-1">omr_engine/pdf/generate.py</code>.
                    Edit the box positions in mm, then run <code className="font-mono bg-white px-1">python -m omr_engine.pdf.generate</code> to rebuild
                    the PDFs and JSON sidecars. The engine and the printed page are produced by the same code path so they can never drift.
                  </p>
                </div>
              </motion.div>
            )}
            {activeTab === 'settings' && (
              <motion.div
                key="settings"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div>
                  <h3 className="font-serif italic text-2xl">Settings</h3>
                  <p className="text-xs opacity-60 mt-1">Engine status, defaults, and resources</p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="border border-[#141414] bg-white p-5">
                    <h4 className="text-[10px] uppercase tracking-widest font-bold opacity-50 mb-3">Engine</h4>
                    <div className="space-y-2 text-[11px] font-mono">
                      <div className="flex justify-between">
                        <span className="opacity-60">Status</span>
                        <span className={cn(
                          "px-1.5 py-0.5 rounded font-bold uppercase text-[9px]",
                          engineHealthy ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                        )}>
                          {engineHealthy ? 'Healthy' : 'Unreachable'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="opacity-60">Bridge</span>
                        <span>/api → :8000</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="opacity-60">Templates loaded</span>
                        <span>{availableTemplates.length}</span>
                      </div>
                    </div>
                  </div>

                  <div className="border border-[#141414] bg-white p-5">
                    <h4 className="text-[10px] uppercase tracking-widest font-bold opacity-50 mb-3">Upload defaults</h4>
                    <div className="space-y-2 text-[11px] font-mono">
                      <div className="flex justify-between">
                        <span className="opacity-60">Template</span>
                        <span>AE_STANDARD</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="opacity-60">Answer key</span>
                        <span>AE_STANDARD_KEY</span>
                      </div>
                    </div>
                    <p className="text-[10px] opacity-50 mt-3">
                      Used for new sessions created via the New Scan button.
                    </p>
                  </div>

                  <div className="border border-[#141414] bg-white p-5">
                    <h4 className="text-[10px] uppercase tracking-widest font-bold opacity-50 mb-3">Sensitivity (env vars)</h4>
                    <div className="space-y-2 text-[11px] font-mono">
                      <div className="flex justify-between">
                        <span className="opacity-60">OMR_MARKED_THRESHOLD</span>
                        <span>0.18</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="opacity-60">OMR_BLANK_THRESHOLD</span>
                        <span>0.04</span>
                      </div>
                    </div>
                    <p className="text-[10px] opacity-50 mt-3">
                      Set in <code className="font-mono bg-[#f9f9f9] px-1">.env</code> and restart the Python engine to change.
                    </p>
                  </div>

                  <div className="border border-[#141414] bg-white p-5">
                    <h4 className="text-[10px] uppercase tracking-widest font-bold opacity-50 mb-3">Resources</h4>
                    <div className="space-y-1.5">
                      <a href="/api/templates" target="_blank" rel="noreferrer" className="block text-[11px] hover:underline">
                        → Available templates (JSON)
                      </a>
                      <a href="/api/answer-keys" target="_blank" rel="noreferrer" className="block text-[11px] hover:underline">
                        → Available answer keys (JSON)
                      </a>
                      <a href="/api/sessions" target="_blank" rel="noreferrer" className="block text-[11px] hover:underline">
                        → All sessions (JSON)
                      </a>
                    </div>
                  </div>
                </div>

                <div className="border border-[#141414] bg-blue-50 p-4 text-[11px] leading-relaxed">
                  <p className="font-bold uppercase tracking-widest mb-1">Anthropic API key</p>
                  <p className="opacity-70">
                    Required for the Claude vision fallback on ambiguous marks. Set <code className="font-mono bg-white px-1">ANTHROPIC_API_KEY</code> in <code className="font-mono bg-white px-1">.env</code>.
                    Without it the pipeline still works — ambiguous boxes just stay ambiguous and require manual review in the queue.
                  </p>
                </div>
              </motion.div>
            )}

            {activeTab === 'export' && (
              <motion.div
                key="export"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="space-y-6"
              >
                <div className="flex justify-between items-end gap-4">
                  <div>
                    <h3 className="font-serif italic text-2xl">Data Export</h3>
                    <p className="text-xs opacity-60 mt-1">Export results to CSV or Excel for school management systems</p>
                  </div>
                  <div className="flex gap-2 items-center">
                    <select
                      value={selectedSessionId || ''}
                      onChange={(e) => setSelectedSessionId(e.target.value || null)}
                      className="border border-[#141414] px-3 py-2 text-[10px] uppercase font-bold bg-white"
                    >
                      <option value="">Select a session…</option>
                      {sessions.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                    <a
                      href={selectedSessionId ? api.exportCsvUrl(selectedSessionId) : '#'}
                      onClick={(e) => { if (!selectedSessionId) e.preventDefault(); }}
                      className={cn(
                        "bg-[#141414] text-white px-4 py-2 text-[10px] uppercase font-bold hover:bg-[#333] transition-colors flex items-center gap-2",
                        !selectedSessionId && "opacity-30 cursor-not-allowed pointer-events-none"
                      )}
                    >
                      <Download size={14} />
                      Export CSV
                    </a>
                    <a
                      href={selectedSessionId ? api.exportXlsxUrl(selectedSessionId) : '#'}
                      onClick={(e) => { if (!selectedSessionId) e.preventDefault(); }}
                      className={cn(
                        "border border-[#141414] px-4 py-2 text-[10px] uppercase font-bold hover:bg-[#141414] hover:text-white transition-colors flex items-center gap-2",
                        !selectedSessionId && "opacity-30 cursor-not-allowed pointer-events-none"
                      )}
                    >
                      <Download size={14} />
                      Export XLSX
                    </a>
                  </div>
                </div>

                <div className="border border-[#141414] bg-white overflow-hidden">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[#141414] text-[10px] uppercase tracking-widest opacity-50 bg-[#f9f9f9]">
                        <th className="p-4 font-normal">Student ID</th>
                        <th className="p-4 font-normal">Name</th>
                        <th className="p-4 font-normal">Score</th>
                        <th className="p-4 font-normal">Wrong Qs</th>
                        <th className="p-4 font-normal">Ambiguous</th>
                        <th className="p-4 font-normal">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="text-[11px] font-mono">
                      {sessionSheets.length === 0 && (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-[11px] uppercase tracking-widest opacity-50">
                            {selectedSessionId ? 'No sheets in this session yet' : 'Select a session to view its sheets'}
                          </td>
                        </tr>
                      )}
                      {sessionSheets.map((sheet) => {
                        const score = sheet.score;
                        const wrongQs = score?.wrong_question_ids || [];
                        return (
                          <tr key={sheet.sheet_id} className="border-b border-[#141414]/10">
                            <td className="p-4">{sheet.student_id || '—'}</td>
                            <td className="p-4 font-sans font-bold">{sheet.student_name || '—'}</td>
                            <td className="p-4 text-green-600">
                              {score ? `${score.total_points}/${score.points_possible}` : '—'}
                            </td>
                            <td className="p-4">
                              {wrongQs.length === 0
                                ? '—'
                                : wrongQs.slice(0, 6).map(q => `Q${q}`).join(', ') + (wrongQs.length > 6 ? '…' : '')}
                            </td>
                            <td className="p-4">{score?.ambiguous_question_ids.length ?? 0}</td>
                            <td className="p-4 opacity-50">{sheet.created_at.replace('T', ' ').slice(0, 16)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
            {activeTab === 'review' && (
              <motion.div
                key="review"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className="space-y-6"
              >
                <div className="flex justify-between items-end gap-4">
                  <div>
                    <h3 className="font-serif italic text-2xl">Review Queue</h3>
                    <p className="text-xs opacity-60 mt-1">
                      {reviewCount === 0
                        ? 'No ambiguous marks pending'
                        : `${reviewCount} mark${reviewCount === 1 ? '' : 's'} flagged by AI for manual verification`}
                    </p>
                  </div>
                  <div className="flex gap-2 items-center">
                    <select
                      value={selectedSessionId || ''}
                      onChange={(e) => setSelectedSessionId(e.target.value || null)}
                      className="border border-[#141414] px-3 py-2 text-[10px] uppercase font-bold bg-white"
                    >
                      <option value="">Select a session…</option>
                      {sessions.map(s => (
                        <option key={s.id} value={s.id}>{s.name}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {reviewCount === 0 ? (
                  <div className="border border-[#141414] bg-white p-12 text-center text-[11px] uppercase tracking-widest opacity-50">
                    {selectedSessionId
                      ? 'All marks classified with high confidence — nothing to review'
                      : 'Select a session to load its review queue'}
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {sessionSheets.flatMap(sheet =>
                      sheet.process_result.boxes
                        .map((box, idx) => ({ box, idx }))
                        .filter(({ box }) => box.source === 'claude')
                        .map(({ box, idx }) => (
                          <ReviewCard
                            key={`${sheet.sheet_id}-${idx}`}
                            questionLabel={`Q${box.question_id}.${box.option}`}
                            studentLabel={
                              sheet.student_id || sheet.student_name
                                ? `${sheet.student_id || ''} ${sheet.student_name || ''}`.trim()
                                : `Sheet ${sheet.sheet_id}`
                            }
                            status={box.status}
                            reason={box.reason || 'AI escalation'}
                            imageB64={box.image_b64}
                            onOverride={(s) => handleOverride(sheet.sheet_id, idx, s)}
                          />
                        ))
                    )}
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

// --- Sub-components ---

function NavItem({ icon, label, active, onClick, badge }: { icon: React.ReactNode, label: string, active?: boolean, onClick: () => void, badge?: number }) {
  return (
    <button 
      onClick={onClick}
      className={cn(
        "w-full flex items-center justify-between px-4 py-3 text-xs font-bold uppercase tracking-widest transition-all group",
        active ? "bg-[#141414] text-[#E4E3E0]" : "hover:bg-[#141414]/5"
      )}
    >
      <div className="flex items-center gap-3">
        <span className={cn("transition-transform group-hover:scale-110", active ? "text-[#E4E3E0]" : "text-[#141414]")}>
          {icon}
        </span>
        {label}
      </div>
      {badge && (
        <span className={cn(
          "text-[9px] px-1.5 py-0.5 rounded-full font-mono",
          active ? "bg-white text-[#141414]" : "bg-[#141414] text-white"
        )}>
          {badge}
        </span>
      )}
    </button>
  );
}

function StatCard({ label, value, delta, warning }: { label: string, value: string, delta: string, warning?: boolean }) {
  return (
    <div className={cn(
      "border border-[#141414] p-6 bg-white flex flex-col justify-between h-32 transition-transform hover:-translate-y-1",
      warning && "border-orange-500 bg-orange-50/30"
    )}>
      <span className="text-[10px] uppercase tracking-widest font-bold opacity-50">{label}</span>
      <div className="flex items-baseline justify-between mt-2">
        <span className="text-3xl font-serif italic">{value}</span>
        <span className={cn(
          "text-[10px] font-mono px-1.5 py-0.5 rounded",
          delta.startsWith('+') ? "bg-green-100 text-green-700" : 
          delta.startsWith('-') ? "bg-red-100 text-red-700" : "bg-gray-100"
        )}>
          {delta}
        </span>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: Session['status'] }) {
  const configs = {
    processing: { icon: <Clock size={10} />, label: 'Processing', class: 'bg-blue-100 text-blue-700' },
    completed: { icon: <CheckCircle2 size={10} />, label: 'Completed', class: 'bg-green-100 text-green-700' },
    review_required: { icon: <AlertCircle size={10} />, label: 'Review Required', class: 'bg-orange-100 text-orange-700' },
  };
  const config = configs[status];
  return (
    <div className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-tighter", config.class)}>
      {config.icon}
      {config.label}
    </div>
  );
}

function ReviewCard({
  questionLabel,
  studentLabel,
  status,
  reason,
  imageB64,
  onOverride,
}: {
  questionLabel: string;
  studentLabel: string;
  status: 'marked' | 'blank' | 'ambiguous';
  reason: string;
  imageB64: string | null;
  onOverride: (status: 'marked' | 'blank') => void | Promise<void>;
}) {
  const imageSrc = imageB64 ? `data:image/png;base64,${imageB64}` : null;
  return (
    <div className="border border-[#141414] bg-white overflow-hidden group hover:shadow-lg transition-shadow">
      <div className="p-4 border-b border-[#141414] flex justify-between items-center bg-[#f9f9f9]">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold bg-[#141414] text-white px-2 py-0.5">{questionLabel}</span>
          <span className="text-[11px] font-bold uppercase tracking-tight">{studentLabel}</span>
        </div>
        <span className={cn(
          "text-[9px] font-mono px-1.5 py-0.5 rounded uppercase",
          status === 'marked' && "bg-green-100 text-green-700",
          status === 'blank' && "bg-gray-100 text-gray-700",
          status === 'ambiguous' && "bg-orange-100 text-orange-700",
        )}>
          {status}
        </span>
      </div>

      <div className="p-6 space-y-4">
        <div className="aspect-[5/2] bg-[#E4E3E0] border border-[#141414]/10 relative overflow-hidden flex items-center justify-center">
          {imageSrc ? (
            <img
              src={imageSrc}
              alt={`Crop for ${questionLabel}`}
              className="max-w-full max-h-full object-contain"
            />
          ) : (
            <span className="text-[10px] uppercase opacity-50">No image available</span>
          )}
          <div className="absolute inset-0 border-[2px] border-orange-500/50 pointer-events-none" />
        </div>

        <div className="flex items-start gap-3 bg-orange-50 p-3 border border-orange-100">
          <AlertCircle size={14} className="text-orange-600 mt-0.5 shrink-0" />
          <p className="text-[11px] leading-relaxed italic text-orange-900">{reason}</p>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => onOverride('marked')}
            className="border border-[#141414] py-2 text-[10px] font-bold uppercase hover:bg-green-500 hover:text-white hover:border-green-600 transition-colors"
          >
            Marked
          </button>
          <button
            onClick={() => onOverride('blank')}
            className="border border-[#141414] py-2 text-[10px] font-bold uppercase hover:bg-gray-200 transition-colors"
          >
            Blank
          </button>
        </div>
      </div>
    </div>
  );
}
