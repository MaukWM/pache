import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api, type KanjiItem } from '../lib/api';

export function KanjiPage() {
  const [includeInactive, setIncludeInactive] = useState(false);
  const [selected, setSelected] = useState<KanjiItem | null>(null);

  const params: Record<string, string> = {};
  if (includeInactive) params.include_inactive = 'true';

  const kanji = useQuery({
    queryKey: ['kanji', params],
    queryFn: () => api.getKanji(Object.keys(params).length ? params : undefined),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Kanji</h1>
        <label className="flex items-center gap-2 text-sm text-text-muted cursor-pointer">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
            className="rounded accent-wk-kanji"
          />
          Show inactive kanji
        </label>
      </div>

      {kanji.isLoading ? (
        <div className="text-text-muted animate-pulse">Loading kanji...</div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {(kanji.data || []).length === 0 ? (
              <div className="bg-surface rounded-xl p-8 text-center text-text-muted w-full">
                No active kanji yet. Create vocabulary to activate kanji!
              </div>
            ) : (
              kanji.data?.map((k) => (
                <button
                  key={k.id}
                  onClick={() => setSelected(k)}
                  className={`w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-lg shadow-sm hover:shadow-md hover:scale-110 transition-all ${
                    k.active ? 'bg-wk-kanji' : 'bg-text-muted'
                  }`}
                  title={k.meanings.join(', ')}
                >
                  {k.character}
                </button>
              ))
            )}
          </div>

          {/* Detail panel */}
          {selected && (
            <KanjiDetail kanji={selected} onClose={() => setSelected(null)} />
          )}
        </>
      )}
    </div>
  );
}

function KanjiDetail({ kanji, onClose }: { kanji: KanjiItem; onClose: () => void }) {
  return (
    <div className="bg-surface rounded-xl p-6 shadow-md relative">
      <button
        onClick={onClose}
        className="absolute top-3 right-3 text-text-muted hover:text-text text-xl leading-none"
      >
        &times;
      </button>
      <div className="flex items-start gap-6">
        <div className="bg-wk-kanji w-24 h-24 rounded-xl flex items-center justify-center text-white text-5xl font-bold shadow-md shrink-0">
          {kanji.character}
        </div>
        <div className="space-y-3 flex-1">
          <div>
            <h2 className="text-xl font-bold">{kanji.character}</h2>
            <p className="text-text-muted">{kanji.meanings.join(', ')}</p>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-bold text-text-muted block">On'yomi</span>
              <span>{kanji.readings_on.join(', ') || 'None'}</span>
            </div>
            <div>
              <span className="font-bold text-text-muted block">Kun'yomi</span>
              <span>{kanji.readings_kun.join(', ') || 'None'}</span>
            </div>
            {kanji.grade && (
              <div>
                <span className="font-bold text-text-muted block">Grade</span>
                <span>{kanji.grade}</span>
              </div>
            )}
            {kanji.jlpt_level && (
              <div>
                <span className="font-bold text-text-muted block">JLPT</span>
                <span>N{kanji.jlpt_level}</span>
              </div>
            )}
            {kanji.stroke_count && (
              <div>
                <span className="font-bold text-text-muted block">Strokes</span>
                <span>{kanji.stroke_count}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
