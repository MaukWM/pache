import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { SubjectCard } from '../components/SubjectCard';
import { GlyphCell } from '../components/GlyphCell';
import { Section, ProgressionSection } from '../components/SubjectDetail';
import { EditVocabForm, queueVocabAndKanji } from './VocabPage';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

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
      setActionMsg(added > 0 ? `学習キューに追加しました（漢字+${added}件）！` : '学習キューに追加しました！');
      invalidateAll();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const unlearnMutation = useMutation({
    mutationFn: () => api.unlearnItem('vocab', item!.id),
    onSuccess: () => { setActionMsg('学習を取り消しました！復習からも削除されました。'); setConfirmUnlearn(false); invalidateAll(); },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const resurrectMutation = useMutation({
    mutationFn: () => api.resurrectItem('vocab', item!.id),
    onSuccess: () => { setActionMsg('見習いIに復活しました！最初の復習は4時間後です。'); setConfirmResurrect(false); invalidateAll(); },
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
        `「${item!.word}」を完全に削除しますか？\n\n全員の共有プールから削除され、` +
          `学習キューの項目とすべてのユーザーの復習進捗も削除されます。` +
          `リンクされた例文は保持されます。この操作は取り消せません。`,
      )
    ) {
      deleteMut.mutate();
    }
  };

  if (vocabQuery.isLoading) {
    return <div className="text-muted-foreground animate-pulse py-10 text-center">読み込み中…</div>;
  }
  if (!item) {
    return (
      <div className="space-y-3 text-center py-10">
        <p className="text-muted-foreground">語彙が見つかりません。</p>
        <Link to="/vocab" className="text-wk-vocab font-bold">← 語彙一覧へ戻る</Link>
      </div>
    );
  }

  if (editing) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <Button variant="ghost" size="sm" onClick={() => setEditing(false)} className="text-muted-foreground">← 編集をキャンセル</Button>
        <Card className="overflow-hidden p-0">
          <EditVocabForm item={item} queryClient={queryClient} onDone={() => { setEditing(false); refetchVocab(); }} />
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="text-muted-foreground">← 戻る</Button>

      {/* Hero */}
      <Card className="flex-row items-center gap-5 p-6">
        <GlyphCell type="vocab" character={item.word} srsStage={currentStage} size="lg" />
        <div className="min-w-0">
          <h1 className="text-3xl font-bold">{item.meanings[0]}</h1>
          {item.meanings.length > 1 && (
            <p className="text-muted-foreground">{item.meanings.slice(1).join(', ')}</p>
          )}
          <p lang="ja" className="text-muted-foreground mt-1">{item.readings.join('、')}</p>
          <div className="flex items-center gap-2 flex-wrap mt-2 text-xs">
            {item.tags?.map((t) => (
              <Badge key={t.id} variant="secondary">{t.name}</Badge>
            ))}
            {item.creator_comment && <span className="text-muted-foreground italic">"{item.creator_comment}"</span>}
            {item.creator_username && <span className="text-muted-foreground">作成者: {item.creator_username}</span>}
          </div>
        </div>
      </Card>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        {!alreadyLearned && (
          <Button onClick={() => queueMutation.mutate()} disabled={queueMutation.isPending}>
            {queueMutation.isPending ? '追加中…' : '学習キューに追加'}
          </Button>
        )}
        {alreadyLearned && isBurned && !confirmResurrect && (
          <Button onClick={() => setConfirmResurrect(true)} className="border border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20 hover:text-destructive">復活</Button>
        )}
        {alreadyLearned && !confirmUnlearn && (
          <Button variant="outline" onClick={() => setConfirmUnlearn(true)}>学習を取り消す</Button>
        )}
        <div className="ml-auto flex items-center gap-2">
          <Button variant="outline" onClick={() => setEditing(true)}>編集</Button>
          <Button variant="outline" onClick={handleDelete} disabled={deleteMut.isPending}
            className="border-destructive/40 text-destructive hover:bg-destructive/10 hover:text-destructive">
            {deleteMut.isPending ? '削除中…' : '削除'}
          </Button>
        </div>
      </div>
      {confirmResurrect && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">{item.word}を見習いIに復活しますか？</span>
          <Button size="sm" onClick={() => resurrectMutation.mutate()} disabled={resurrectMutation.isPending} className="border border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20 hover:text-destructive">はい</Button>
          <Button size="sm" variant="outline" onClick={() => setConfirmResurrect(false)}>キャンセル</Button>
        </div>
      )}
      {confirmUnlearn && (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-destructive">{item.word}の学習を取り消しますか？進捗と復習が削除されます。</span>
          <Button size="sm" variant="destructive" onClick={() => unlearnMutation.mutate()} disabled={unlearnMutation.isPending}>はい</Button>
          <Button size="sm" variant="outline" onClick={() => setConfirmUnlearn(false)}>キャンセル</Button>
        </div>
      )}
      {actionMsg && <p className={`text-sm ${actionMsg.includes('！') ? 'text-success' : 'text-destructive'}`}>{actionMsg}</p>}

      {/* Kanji Composition */}
      {item.kanji && item.kanji.length > 0 && (
        <Section title="漢字構成">
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
      <Section title="意味">
        <p className="text-lg">{item.meanings.join(', ')}</p>
      </Section>

      {/* Reading */}
      <Section title="読み">
        <p lang="ja" className="text-lg">{item.readings.join('、')}</p>
      </Section>

      {/* Context — example sentences */}
      <Section
        title="例文"
        action={
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={() => { setShowAddSentence(!showAddSentence); setShowSuggest(false); }}
              className="h-auto px-1 py-0 text-xs font-bold text-muted-foreground hover:text-wk-vocab hover:bg-transparent">
              {showAddSentence ? 'キャンセル' : '＋例文'}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => { setShowSuggest(!showSuggest); setShowAddSentence(false); }}
              className="h-auto px-1 py-0 text-xs font-bold text-muted-foreground hover:text-wk-vocab hover:bg-transparent">
              {showSuggest ? 'キャンセル' : '例文を探す'}
            </Button>
          </div>
        }
      >
        <div className="space-y-1.5">
          {item.sentences.map((s) =>
            editingSentenceId === s.id ? (
              <div key={s.id} className="flex gap-2">
                <div className="flex-1 space-y-1">
                  <Input type="text" value={editJa} onChange={(e) => setEditJa(e.target.value)} lang="ja"
                    className="h-auto py-1.5 text-sm" />
                  <Input type="text" value={editEn} onChange={(e) => setEditEn(e.target.value)}
                    className="h-auto py-1.5 text-sm" />
                </div>
                <div className="flex flex-col gap-1 self-end">
                  <Button size="sm" onClick={() => updateSentenceMut.mutate({ sid: s.id, ja: editJa.trim(), en: editEn.trim() })}
                    disabled={!editJa.trim() || !editEn.trim() || updateSentenceMut.isPending}>保存</Button>
                  <Button size="sm" variant="outline" onClick={() => setEditingSentenceId(null)}>キャンセル</Button>
                </div>
              </div>
            ) : (
              <div key={s.id} className="bg-muted rounded-lg px-3 py-2 text-sm group relative">
                <p lang="ja">{s.ja}</p>
                <p className="text-muted-foreground text-xs">{s.en}</p>
                <div className="absolute top-1 right-2 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button onClick={() => { setEditingSentenceId(s.id); setEditJa(s.ja); setEditEn(s.en); }}
                    className="text-muted-foreground hover:text-wk-vocab text-xs" title="例文を編集">&#9998;</button>
                  <button onClick={() => unlinkMut.mutate(s.id)} className="text-muted-foreground hover:text-destructive text-xs" title="例文のリンクを解除">&times;</button>
                </div>
              </div>
            ),
          )}
          {item.sentences.length === 0 && !showAddSentence && !showSuggest && (
            <p className="text-sm text-muted-foreground">まだ例文がありません。</p>
          )}
          {showAddSentence && (
            <div className="flex gap-2">
              <div className="flex-1 space-y-1">
                <Input type="text" value={newJa} onChange={(e) => setNewJa(e.target.value)} placeholder="日本語..." lang="ja"
                  className="h-auto py-1.5 text-sm" />
                <Input type="text" value={newEn} onChange={(e) => setNewEn(e.target.value)} placeholder="英語..."
                  className="h-auto py-1.5 text-sm" />
              </div>
              <Button size="sm" className="self-end" onClick={() => createSentenceMut.mutate()} disabled={!newJa.trim() || !newEn.trim() || createSentenceMut.isPending}>追加</Button>
            </div>
          )}
          {showSuggest && (
            <div className="space-y-1">
              {suggestions.isLoading && <p className="text-xs text-muted-foreground animate-pulse">検索中...</p>}
              {suggestions.data?.length === 0 && <p className="text-xs text-muted-foreground">一致する例文が見つかりません。</p>}
              {suggestions.data?.map((s) => (
                <div key={s.id} className="bg-muted rounded-lg px-3 py-1.5 text-sm flex items-center gap-2">
                  <div className="flex-1 min-w-0">
                    <span lang="ja">{s.ja}</span>
                    <span className="text-muted-foreground text-xs ml-2">{s.en}</span>
                  </div>
                  <Button variant="link" size="sm" onClick={() => linkMut.mutate(s.id)} className="h-auto p-0 text-xs text-wk-vocab font-bold shrink-0">リンク</Button>
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
