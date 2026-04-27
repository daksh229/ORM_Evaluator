import React from 'react';

// --- Template layout definitions ---
// Each entry describes how many questions, which options per section,
// and how many columns. This mirrors the Python builders in
// omr_engine/pdf/generate.py but is purely for the in-app visual preview.

interface SectionDef {
  title?: string;
  options: string[];
  questions: number[];    // list of question IDs
  multiMark?: boolean;
}

interface TemplateDef {
  name: string;
  subtitle: string;
  columns: number;
  sections: SectionDef[];
}

const TEMPLATE_DEFS: Record<string, TemplateDef> = {
  AE_STANDARD: {
    name: 'Mock Exam Answer Sheet',
    subtitle: 'GL-Style A-E Standard (50 questions)',
    columns: 2,
    sections: [
      {
        options: ['A', 'B', 'C', 'D', 'E'],
        questions: Array.from({ length: 50 }, (_, i) => i + 1),
      },
    ],
  },
  ADN_STANDARD: {
    name: 'Mock Exam Answer Sheet',
    subtitle: 'GL-Style A / D / N Variant (50 questions)',
    columns: 2,
    sections: [
      {
        options: ['A', 'D', 'N'],
        questions: Array.from({ length: 50 }, (_, i) => i + 1),
      },
    ],
  },
  MULTI_SECTION: {
    name: 'Mock Exam Answer Sheet',
    subtitle: 'Multi-Section Layout',
    columns: 1,
    sections: [
      {
        title: 'Section 1 — Verbal Reasoning (A-E)',
        options: ['A', 'B', 'C', 'D', 'E'],
        questions: Array.from({ length: 15 }, (_, i) => i + 1),
      },
      {
        title: 'Section 2 — Numerical (A-D)',
        options: ['A', 'B', 'C', 'D'],
        questions: Array.from({ length: 15 }, (_, i) => i + 16),
      },
      {
        title: 'Section 3 — True / False',
        options: ['T', 'F'],
        questions: Array.from({ length: 10 }, (_, i) => i + 31),
      },
    ],
  },
  AE_TWOMARK: {
    name: 'Mock Exam Answer Sheet',
    subtitle: 'A-E with Multi-Mark Section',
    columns: 1,
    sections: [
      {
        title: 'Single mark per question',
        options: ['A', 'B', 'C', 'D', 'E'],
        questions: Array.from({ length: 20 }, (_, i) => i + 1),
      },
      {
        title: 'Mark TWO answers per question',
        options: ['A', 'B', 'C', 'D', 'E'],
        questions: Array.from({ length: 10 }, (_, i) => i + 21),
        multiMark: true,
      },
    ],
  },
};

// --- Sub-components ---

function OMRBox({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <div className="w-7 h-3.5 border border-[#141414] bg-white" />
      <span className="text-[8px] font-bold opacity-50">{label}</span>
    </div>
  );
}

function QuestionRow({ qid, options, multiMark }: { qid: number; options: string[]; multiMark?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-5 text-right text-[9px] font-mono font-bold shrink-0">{qid}</span>
      <div className="flex gap-1.5">
        {options.map(opt => (
          <OMRBox key={opt} label={opt} />
        ))}
      </div>
      {multiMark && (
        <span className="text-[7px] font-mono opacity-40 ml-1">[2]</span>
      )}
    </div>
  );
}

// --- Main component ---

export function GLStyleSheetPreview({ templateId }: { templateId: string }) {
  const def = TEMPLATE_DEFS[templateId];

  if (!def) {
    return (
      <div className="bg-white p-12 shadow-2xl border border-[#141414]/10 max-w-[600px] mx-auto text-center">
        <p className="text-[11px] uppercase tracking-widest opacity-50">
          No preview available for template "{templateId}"
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white p-8 shadow-2xl border border-[#141414]/10 max-w-[640px] mx-auto font-sans">
      {/* Header */}
      <div className="flex justify-between items-start border-b-2 border-[#141414] pb-3 mb-6">
        <div>
          <h2 className="text-lg font-bold uppercase tracking-tighter">{def.name}</h2>
          <p className="text-[9px] uppercase tracking-widest opacity-60">{def.subtitle}</p>
        </div>
        <div className="flex gap-1">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="w-2.5 h-2.5 bg-[#141414]" />
          ))}
        </div>
      </div>

      <p className="text-[8px] uppercase tracking-widest opacity-40 mb-6">
        Mark each answer with a single thin horizontal line in the chosen box
      </p>

      {/* Sections */}
      {def.sections.map((section, si) => {
        const half = Math.ceil(section.questions.length / 2);
        const col1 = def.columns === 2 ? section.questions.slice(0, half) : section.questions;
        const col2 = def.columns === 2 ? section.questions.slice(half) : [];

        return (
          <div key={si} className="mb-6">
            {section.title && (
              <h3 className="text-[9px] font-bold uppercase tracking-widest mb-3 border-b border-[#141414]/10 pb-1">
                {section.title}
              </h3>
            )}

            {/* Option headers */}
            <div className={`grid ${def.columns === 2 ? 'grid-cols-2 gap-8' : 'grid-cols-1'} mb-2`}>
              <div className="flex items-center gap-3">
                <span className="w-5" />
                <div className="flex gap-1.5">
                  {section.options.map(o => (
                    <span key={o} className="w-7 text-center text-[8px] font-bold opacity-50">{o}</span>
                  ))}
                </div>
              </div>
              {col2.length > 0 && (
                <div className="flex items-center gap-3">
                  <span className="w-5" />
                  <div className="flex gap-1.5">
                    {section.options.map(o => (
                      <span key={o} className="w-7 text-center text-[8px] font-bold opacity-50">{o}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Question rows */}
            <div className={`grid ${def.columns === 2 ? 'grid-cols-2 gap-x-8 gap-y-2' : 'grid-cols-1 gap-y-2'}`}>
              {def.columns === 2 ? (
                <>
                  {col1.map((qid, i) => (
                    <React.Fragment key={qid}>
                      <QuestionRow qid={qid} options={section.options} multiMark={section.multiMark} />
                      {col2[i] !== undefined ? (
                        <QuestionRow qid={col2[i]} options={section.options} multiMark={section.multiMark} />
                      ) : (
                        <div />
                      )}
                    </React.Fragment>
                  ))}
                </>
              ) : (
                col1.map(qid => (
                  <QuestionRow key={qid} qid={qid} options={section.options} multiMark={section.multiMark} />
                ))
              )}
            </div>
          </div>
        );
      })}

      {/* Footer */}
      <div className="mt-6 pt-3 border-t border-[#141414]/20 flex justify-between items-center opacity-40">
        <span className="text-[7px] uppercase tracking-widest">Do not fold or smudge this sheet</span>
        <span className="text-[7px] font-mono">Template {templateId}</span>
      </div>
    </div>
  );
}
