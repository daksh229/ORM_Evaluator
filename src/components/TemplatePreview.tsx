import React from 'react';
import { cn } from '../lib/utils';

interface BoxProps {
  label: string;
  marked?: boolean;
  key?: string | number;
}

function OMRBox({ label, marked }: BoxProps) {
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative w-8 h-4 border border-[#141414] bg-white flex items-center justify-center">
        {marked && (
          <div className="w-6 h-[2px] bg-[#141414] rounded-full" />
        )}
      </div>
      <span className="text-[9px] font-bold opacity-60">{label}</span>
    </div>
  );
}

export function GLStyleSheetPreview() {
  return (
    <div className="bg-white p-12 shadow-2xl border border-[#141414]/10 max-w-[600px] mx-auto font-sans">
      <div className="flex justify-between items-start border-b-2 border-[#141414] pb-4 mb-8">
        <div>
          <h2 className="text-xl font-bold uppercase tracking-tighter">Mock Exam Answer Sheet</h2>
          <p className="text-[10px] uppercase tracking-widest opacity-60">GL-Style Original Template #AE-01</p>
        </div>
        <div className="flex gap-1">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="w-3 h-3 bg-[#141414]" />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-12">
        {/* Column 1 */}
        <div className="space-y-4">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(q => (
            <div key={q} className="flex items-center gap-4">
              <span className="w-4 text-[10px] font-mono font-bold">{q}</span>
              <div className="flex gap-2">
                {['A', 'B', 'C', 'D', 'E'].map(opt => (
                  <OMRBox key={opt} label={opt} marked={q === 3 && opt === 'B'} />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Column 2 */}
        <div className="space-y-4">
          {[11, 12, 13, 14, 15, 16, 17, 18, 19, 20].map(q => (
            <div key={q} className="flex items-center gap-4">
              <span className="w-4 text-[10px] font-mono font-bold">{q}</span>
              <div className="flex gap-2">
                {['A', 'B', 'C', 'D', 'E'].map(opt => (
                  <OMRBox key={opt} label={opt} marked={q === 15 && opt === 'D'} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-12 pt-4 border-t border-[#141414]/20 flex justify-between items-center opacity-40">
        <span className="text-[8px] uppercase tracking-widest">Do not fold or smudge this sheet</span>
        <span className="text-[8px] font-mono">ID: TEMPLATE_VR_AE_2026</span>
      </div>
    </div>
  );
}
