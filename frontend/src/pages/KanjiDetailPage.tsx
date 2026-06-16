import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { RadicalList } from '../components/RadicalList';
import { SubjectCard } from '../components/SubjectCard';
import { Section, ProgressionSection } from '../components/SubjectDetail';
import { katakanaToHiragana } from '../lib/romaji';

export function KanjiDetailPage() {
  const { char } = useParams<{ char: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [actionMsg, setActionMsg] = useState('');
  const [confirmUnlearn, setConfirmUnlearn] = useState(false);
  const [confirmResurrect, setConfirmResurrect] = useState(false);

  const kanjiQuery = useQuery({
    queryKey: ['kanji', 'detail', char],
    queryFn: () => api.getKanjiDetail(char!),
    enabled: !!char,
  });
  const progressMap = useQuery({ queryKey: ['progressMap'], queryFn: api.getProgressMap });

  const kanji = kanjiQuery.data;

  // Vocabulary that contains this kanji (WaniKani's "Found In Vocabulary").
  const foundIn = useQuery({
    queryKey: ['vocab', 'byKanji', kanji?.id],
    queryFn: () => api.getVocab({ kanji_id: String(kanji!.id) }),
    enabled: kanji != null,
  });

  const currentStage = kanji ? progressMap.data?.[`kanji-${kanji.id}`] : undefined;
  const alreadyLearned = currentStage != null;
  const isBurned = currentStage === 9;

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['progressMap'] });
    queryClient.invalidateQueries({ queryKey: ['progress'] });
    queryClient.invalidateQueries({ queryKey: ['reviews'] });
    queryClient.invalidateQueries({ queryKey: ['queue'] });
  };

  const queueMutation = useMutation({
    mutationFn: () => api.addToQueue('kanji', kanji!.id),
    onSuccess: () => {
      setActionMsg('Added to lesson queue!');
      invalidate();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const unlearnMutation = useMutation({
    mutationFn: () => api.unlearnItem('kanji', kanji!.id),
    onSuccess: () => {
      setActionMsg('Unlearned! Removed from your reviews.');
      setConfirmUnlearn(false);
      invalidate();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const resurrectMutation = useMutation({
    mutationFn: () => api.resurrectItem('kanji', kanji!.id),
    onSuccess: () => {
      setActionMsg('Resurrected to Apprentice I! First review in 4 hours.');
      setConfirmResurrect(false);
      invalidate();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  if (kanjiQuery.isLoading) {
    return <div className="text-text-muted animate-pulse py-10 text-center">Loading…</div>;
  }
  if (!kanji) {
    return (
      <div className="space-y-3 text-center py-10">
        <p className="text-text-muted">Kanji not found.</p>
        <Link to="/kanji" className="text-wk-kanji font-bold">← Back to Kanji</Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <button onClick={() => navigate(-1)} className="text-sm text-text-muted hover:text-text">
        ← Back
      </button>

      {/* Hero */}
      <div className="bg-surface rounded-xl p-6 shadow-sm flex items-center gap-5">
        <div className="bg-wk-kanji border-2 border-wk-kanji-dark w-24 h-24 rounded-xl flex items-center justify-center text-white text-5xl font-bold shrink-0" lang="ja">
          {kanji.character}
        </div>
        <div className="min-w-0">
          <h1 className="text-3xl font-bold">{kanji.meanings[0]}</h1>
          {kanji.meanings.length > 1 && (
            <p className="text-text-muted">{kanji.meanings.slice(1).join(', ')}</p>
          )}
          <div className="flex gap-4 flex-wrap text-sm text-text-muted mt-1">
            {kanji.frequency && <span>Freq #{kanji.frequency}</span>}
            {kanji.grade && <span>Grade {kanji.grade}</span>}
            {kanji.jlpt_level && <span>JLPT N{kanji.jlpt_level}</span>}
            {kanji.stroke_count && <span>{kanji.stroke_count} strokes</span>}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        {!alreadyLearned && (
          <button onClick={() => queueMutation.mutate()} disabled={queueMutation.isPending}
            className="px-4 py-2 rounded-lg bg-wk-kanji text-white font-bold text-sm hover:bg-accent-hover transition-colors disabled:opacity-50">
            {queueMutation.isPending ? 'Adding…' : 'Add to Queue'}
          </button>
        )}
        {alreadyLearned && isBurned && !confirmResurrect && (
          <button onClick={() => setConfirmResurrect(true)}
            className="px-4 py-2 rounded-lg bg-wk-radical text-white font-bold text-sm hover:opacity-90">
            Resurrect
          </button>
        )}
        {alreadyLearned && !confirmUnlearn && (
          <button onClick={() => setConfirmUnlearn(true)}
            className="px-4 py-2 rounded-lg bg-surface border border-border text-sm font-bold hover:bg-border">
            Unlearn
          </button>
        )}
        {confirmResurrect && (
          <span className="flex items-center gap-2 text-sm">
            <span className="text-text-muted">Resurrect {kanji.character} to Apprentice I?</span>
            <button onClick={() => resurrectMutation.mutate()} disabled={resurrectMutation.isPending}
              className="px-3 py-1.5 rounded-lg bg-wk-radical text-white font-bold disabled:opacity-50">Yes</button>
            <button onClick={() => setConfirmResurrect(false)} className="px-3 py-1.5 rounded-lg border border-border font-bold hover:bg-border">Cancel</button>
          </span>
        )}
        {confirmUnlearn && (
          <span className="flex items-center gap-2 text-sm">
            <span className="text-error">Unlearn {kanji.character}? Deletes progress + reviews.</span>
            <button onClick={() => unlearnMutation.mutate()} disabled={unlearnMutation.isPending}
              className="px-3 py-1.5 rounded-lg bg-error text-white font-bold disabled:opacity-50">Yes</button>
            <button onClick={() => setConfirmUnlearn(false)} className="px-3 py-1.5 rounded-lg border border-border font-bold hover:bg-border">Cancel</button>
          </span>
        )}
      </div>
      {actionMsg && (
        <p className={`text-sm ${actionMsg.includes('!') ? 'text-success' : 'text-error'}`}>{actionMsg}</p>
      )}

      {/* Radicals */}
      {kanji.components && kanji.components.length > 0 && (
        <Section title="Radical Combination">
          <RadicalList components={kanji.components} size="sm" />
        </Section>
      )}

      {/* Meaning */}
      <Section title="Meaning">
        <p className="text-lg">{kanji.meanings.join(', ')}</p>
      </Section>

      {/* Readings */}
      <Section title="Readings">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-text-muted text-xs block mb-0.5">On'yomi</span>
            <span lang="ja" className="text-lg">
              {kanji.readings_on.map(katakanaToHiragana).join('、') || 'None'}
            </span>
          </div>
          <div>
            <span className="text-text-muted text-xs block mb-0.5">Kun'yomi</span>
            <span lang="ja" className="text-lg">{kanji.readings_kun.join('、') || 'None'}</span>
          </div>
        </div>
      </Section>

      {/* Found in Vocabulary */}
      <Section title="Found in Vocabulary">
        {foundIn.isLoading ? (
          <p className="text-sm text-text-muted animate-pulse">Loading…</p>
        ) : foundIn.data && foundIn.data.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {foundIn.data.map((v) => (
              <SubjectCard
                key={v.id}
                type="vocab"
                character={v.word}
                reading={v.readings[0]}
                meaning={v.meanings[0]}
                srsStage={progressMap.data?.[`vocab-${v.id}`]}
                to={`/vocab/${v.id}`}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-muted">No vocabulary uses this kanji yet.</p>
        )}
      </Section>

      <ProgressionSection itemType="kanji" itemId={kanji.id} />
    </div>
  );
}
