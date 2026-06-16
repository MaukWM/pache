import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { SubjectCard } from '../components/SubjectCard';
import { Section, ProgressionSection } from '../components/SubjectDetail';
import { EditVocabForm, queueVocabAndKanji } from './VocabPage';

export function VocabDetailPage() {
  const { id } = useParams<{ id: string }>();
  const vocabId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [actionMsg, setActionMsg] = useState('');
  const [editing, setEditing] = useState(false);
  const [showAddSentence, setShowAddSentence] = useState(false);
  const [showSuggest, setShowSuggest] = useState(false);
  const [newJa, setNewJa] = useState('');
  const [newEn, setNewEn] = useState('');
  const [editingSentenceId, setEditingSentenceId] = useState<number | null>(null);
  const [editJa, setEditJa] = useState('');
  const [editEn, setEditEn] = useState('');
  const [confirmUnlearn, setConfirmUnlearn] = useState(false);
  const [confirmResurrect, setConfirmResurrect] = useState(false);

  const vocabQuery = useQuery({
    queryKey: ['vocab', 'detail', vocabId],
    queryFn: () => api.getVocabById(vocabId),
    enabled: Number.isFinite(vocabId),
  });
  const progressMap = useQuery({ queryKey: ['progressMap'], queryFn: api.getProgressMap });
  const item = vocabQuery.data;

  const currentStage = item ? progressMap.data?.[`vocab-${item.id}`] : undefined;
  const alreadyLearned = currentStage != null;
  const isBurned = currentStage === 9;

  const refetchVocab = () =>
    queryClient.invalidateQueries({ queryKey: ['vocab', 'detail', vocabId] });
  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['vocab'] });
    queryClient.invalidateQueries({ queryKey: ['progressMap'] });
    queryClient.invalidateQueries({ queryKey: ['progress'] });
    queryClient.invalidateQueries({ queryKey: ['reviews'] });
    queryClient.invalidateQueries({ queryKey: ['queue'] });
  };

  const queueMutation = useMutation({
    mutationFn: () => queueVocabAndKanji(item!.id, item!.kanji ?? [], progressMap.data),
    onSuccess: (added) => {
      setActionMsg(added > 0 ? `Added to lesson queue (+${added} kanji)!` : 'Added to lesson queue!');
      invalidateAll();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const unlearnMutation = useMutation({
    mutationFn: () => api.unlearnItem('vocab', item!.id),
    onSuccess: () => { setActionMsg('Unlearned! Removed from your reviews.'); setConfirmUnlearn(false); invalidateAll(); },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const resurrectMutation = useMutation({
    mutationFn: () => api.resurrectItem('vocab', item!.id),
    onSuccess: () => { setActionMsg('Resurrected to Apprentice I! First review in 4 hours.'); setConfirmResurrect(false); invalidateAll(); },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const deleteMut = useMutation({
    mutationFn: () => api.deleteVocab(item!.id),
    onSuccess: () => { invalidateAll(); navigate('/vocab'); },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const createSentenceMut = useMutation({
    mutationFn: () => api.createSentence(item!.id, newJa.trim(), newEn.trim()),
    onSuccess: () => { refetchVocab(); setShowAddSentence(false); setNewJa(''); setNewEn(''); },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const updateSentenceMut = useMutation({
    mutationFn: ({ sid, ja, en }: { sid: number; ja: string; en: string }) =>
      api.updateSentence(item!.id, sid, ja, en),
    onSuccess: () => { refetchVocab(); setEditingSentenceId(null); },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const linkMut = useMutation({
    mutationFn: (sid: number) => api.linkSentence(item!.id, sid),
    onSuccess: refetchVocab,
    onError: (err: Error) => setActionMsg(err.message),
  });
  const unlinkMut = useMutation({
    mutationFn: (sid: number) => api.unlinkSentence(item!.id, sid),
    onSuccess: refetchVocab,
    onError: (err: Error) => setActionMsg(err.message),
  });
  const suggestions = useQuery({
    queryKey: ['vocab', vocabId, 'suggest'],
    queryFn: () => api.suggestSentences(vocabId),
    enabled: showSuggest && Number.isFinite(vocabId),
  });

  const handleDelete = () => {
    if (
      window.confirm(
        `Delete "${item!.word}" permanently?\n\nThis removes it from the shared pool for everyone, ` +
          `along with its lesson-queue entries and all users' review progress for it. ` +
          `Linked example sentences are kept. This cannot be undone.`,
      )
    ) {
      deleteMut.mutate();
    }
  };

  if (vocabQuery.isLoading) {
    return <div className="text-text-muted animate-pulse py-10 text-center">Loading…</div>;
  }
  if (!item) {
    return (
      <div className="space-y-3 text-center py-10">
        <p className="text-text-muted">Vocabulary not found.</p>
        <Link to="/vocab" className="text-wk-vocab font-bold">← Back to Vocabulary</Link>
      </div>
    );
  }

  if (editing) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <button onClick={() => setEditing(false)} className="text-sm text-text-muted hover:text-text">← Cancel edit</button>
        <div className="bg-surface rounded-xl shadow-sm overflow-hidden">
          <EditVocabForm item={item} queryClient={queryClient} onDone={() => { setEditing(false); refetchVocab(); }} />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <button onClick={() => navigate(-1)} className="text-sm text-text-muted hover:text-text">← Back</button>

      {/* Hero */}
      <div className="bg-surface rounded-xl p-6 shadow-sm flex items-center gap-5">
        <div className="bg-wk-vocab border-2 border-wk-vocab-dark px-5 py-3 rounded-xl flex items-center justify-center text-white text-4xl font-bold shrink-0 whitespace-nowrap" lang="ja">
          {item.word}
        </div>
        <div className="min-w-0">
          <h1 className="text-3xl font-bold">{item.meanings[0]}</h1>
          {item.meanings.length > 1 && (
            <p className="text-text-muted">{item.meanings.slice(1).join(', ')}</p>
          )}
          <p lang="ja" className="text-text-muted mt-1">{item.readings.join('、')}</p>
          <div className="flex items-center gap-2 flex-wrap mt-2 text-xs">
            {item.tags?.map((t) => (
              <span key={t.id} className="bg-wk-vocab/10 text-wk-vocab px-2 py-0.5 rounded-full font-medium">{t.name}</span>
            ))}
            {item.creator_comment && <span className="text-text-muted italic">"{item.creator_comment}"</span>}
            {item.creator_username && <span className="text-text-muted">by {item.creator_username}</span>}
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        {!alreadyLearned && (
          <button onClick={() => queueMutation.mutate()} disabled={queueMutation.isPending}
            className="px-4 py-2 rounded-lg bg-wk-vocab text-white font-bold text-sm hover:opacity-90 disabled:opacity-50">
            {queueMutation.isPending ? 'Adding…' : 'Add to Queue'}
          </button>
        )}
        {alreadyLearned && isBurned && !confirmResurrect && (
          <button onClick={() => setConfirmResurrect(true)} className="px-4 py-2 rounded-lg bg-wk-radical text-white font-bold text-sm hover:opacity-90">Resurrect</button>
        )}
        {alreadyLearned && !confirmUnlearn && (
          <button onClick={() => setConfirmUnlearn(true)} className="px-4 py-2 rounded-lg bg-surface border border-border text-sm font-bold hover:bg-border">Unlearn</button>
        )}
        <div className="ml-auto flex items-center gap-2">
          <button onClick={() => setEditing(true)} className="px-4 py-2 rounded-lg bg-surface border border-border text-sm font-bold hover:bg-border">Edit</button>
          <button onClick={handleDelete} disabled={deleteMut.isPending}
            className="px-4 py-2 rounded-lg border border-error/40 text-error text-sm font-bold hover:bg-error/10 disabled:opacity-50">
            {deleteMut.isPending ? 'Deleting…' : 'Delete'}
          </button>
        </div>
      </div>
      {confirmResurrect && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-text-muted">Resurrect {item.word} to Apprentice I?</span>
          <button onClick={() => resurrectMutation.mutate()} disabled={resurrectMutation.isPending} className="px-3 py-1.5 rounded-lg bg-wk-radical text-white font-bold disabled:opacity-50">Yes</button>
          <button onClick={() => setConfirmResurrect(false)} className="px-3 py-1.5 rounded-lg border border-border font-bold hover:bg-border">Cancel</button>
        </div>
      )}
      {confirmUnlearn && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-error">Unlearn {item.word}? Deletes progress + reviews.</span>
          <button onClick={() => unlearnMutation.mutate()} disabled={unlearnMutation.isPending} className="px-3 py-1.5 rounded-lg bg-error text-white font-bold disabled:opacity-50">Yes</button>
          <button onClick={() => setConfirmUnlearn(false)} className="px-3 py-1.5 rounded-lg border border-border font-bold hover:bg-border">Cancel</button>
        </div>
      )}
      {actionMsg && <p className={`text-sm ${actionMsg.includes('!') ? 'text-success' : 'text-error'}`}>{actionMsg}</p>}

      {/* Kanji Composition */}
      {item.kanji && item.kanji.length > 0 && (
        <Section title="Kanji Composition">
          <div className="flex flex-wrap gap-2">
            {item.kanji.map((k) => (
              <SubjectCard
                key={k.id}
                type="kanji"
                character={k.character}
                reading={k.readings_on?.[0] || k.readings_kun?.[0]}
                meaning={k.meanings?.[0]}
                srsStage={progressMap.data?.[`kanji-${k.id}`]}
                to={`/kanji/${encodeURIComponent(k.character)}`}
              />
            ))}
          </div>
        </Section>
      )}

      {/* Meaning */}
      <Section title="Meaning">
        <p className="text-lg">{item.meanings.join(', ')}</p>
      </Section>

      {/* Reading */}
      <Section title="Reading">
        <p lang="ja" className="text-lg">{item.readings.join('、')}</p>
      </Section>

      {/* Context — example sentences */}
      <Section
        title="Context"
        action={
          <div className="flex gap-2">
            <button onClick={() => { setShowAddSentence(!showAddSentence); setShowSuggest(false); }}
              className="text-xs font-bold text-text-muted hover:text-wk-vocab">
              {showAddSentence ? 'Cancel' : '+ Sentence'}
            </button>
            <button onClick={() => { setShowSuggest(!showSuggest); setShowAddSentence(false); }}
              className="text-xs font-bold text-text-muted hover:text-wk-vocab">
              {showSuggest ? 'Cancel' : 'Find Links'}
            </button>
          </div>
        }
      >
        <div className="space-y-1.5">
          {item.sentences.map((s) =>
            editingSentenceId === s.id ? (
              <div key={s.id} className="flex gap-2">
                <div className="flex-1 space-y-1">
                  <input type="text" value={editJa} onChange={(e) => setEditJa(e.target.value)} lang="ja"
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
                  <input type="text" value={editEn} onChange={(e) => setEditEn(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
                </div>
                <div className="flex flex-col gap-1 self-end">
                  <button onClick={() => updateSentenceMut.mutate({ sid: s.id, ja: editJa.trim(), en: editEn.trim() })}
                    disabled={!editJa.trim() || !editEn.trim() || updateSentenceMut.isPending}
                    className="px-3 rounded bg-wk-vocab text-white text-xs font-bold py-1.5 disabled:opacity-50">Save</button>
                  <button onClick={() => setEditingSentenceId(null)} className="px-3 rounded border border-border text-xs font-bold py-1 hover:bg-border">Cancel</button>
                </div>
              </div>
            ) : (
              <div key={s.id} className="bg-surface-alt rounded-lg px-3 py-2 text-sm group relative">
                <p lang="ja">{s.ja}</p>
                <p className="text-text-muted text-xs">{s.en}</p>
                <div className="absolute top-1 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => { setEditingSentenceId(s.id); setEditJa(s.ja); setEditEn(s.en); }}
                    className="text-text-muted hover:text-wk-vocab text-xs" title="Edit sentence">&#9998;</button>
                  <button onClick={() => unlinkMut.mutate(s.id)} className="text-text-muted hover:text-error text-xs" title="Unlink sentence">&times;</button>
                </div>
              </div>
            ),
          )}
          {item.sentences.length === 0 && !showAddSentence && !showSuggest && (
            <p className="text-sm text-text-muted">No example sentences yet.</p>
          )}
          {showAddSentence && (
            <div className="flex gap-2">
              <div className="flex-1 space-y-1">
                <input type="text" value={newJa} onChange={(e) => setNewJa(e.target.value)} placeholder="Japanese..." lang="ja"
                  className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
                <input type="text" value={newEn} onChange={(e) => setNewEn(e.target.value)} placeholder="English..."
                  className="w-full px-2.5 py-1.5 rounded border border-border bg-surface-alt text-sm focus:outline-none focus:ring-1 focus:ring-wk-vocab" />
              </div>
              <button onClick={() => createSentenceMut.mutate()} disabled={!newJa.trim() || !newEn.trim() || createSentenceMut.isPending}
                className="px-3 self-end rounded bg-wk-vocab text-white text-xs font-bold py-1.5 disabled:opacity-50">Add</button>
            </div>
          )}
          {showSuggest && (
            <div className="space-y-1">
              {suggestions.isLoading && <p className="text-xs text-text-muted animate-pulse">Searching...</p>}
              {suggestions.data?.length === 0 && <p className="text-xs text-text-muted">No matches found.</p>}
              {suggestions.data?.map((s) => (
                <div key={s.id} className="bg-surface-alt rounded-lg px-3 py-1.5 text-sm flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <span lang="ja">{s.ja}</span>
                    <span className="text-text-muted text-xs ml-2">{s.en}</span>
                  </div>
                  <button onClick={() => linkMut.mutate(s.id)} className="text-xs text-wk-vocab font-bold hover:underline shrink-0">Link</button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Section>

      <ProgressionSection itemType="vocab" itemId={item.id} />
    </div>
  );
}
