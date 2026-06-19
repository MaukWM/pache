import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../lib/api';
import { RadicalList } from '../components/RadicalList';
import { SubjectCard } from '../components/SubjectCard';
import { GlyphCell } from '../components/GlyphCell';
import { Section, ProgressionSection } from '../components/SubjectDetail';
import { katakanaToHiragana } from '../lib/romaji';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft } from 'lucide-react';

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
      setActionMsg('学習キューに追加しました！');
      invalidate();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const unlearnMutation = useMutation({
    mutationFn: () => api.unlearnItem('kanji', kanji!.id),
    onSuccess: () => {
      setActionMsg('学習を取り消しました！復習からも削除されました。');
      setConfirmUnlearn(false);
      invalidate();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });
  const resurrectMutation = useMutation({
    mutationFn: () => api.resurrectItem('kanji', kanji!.id),
    onSuccess: () => {
      setActionMsg('見習いIに復活しました！最初の復習は4時間後です。');
      setConfirmResurrect(false);
      invalidate();
    },
    onError: (err: Error) => setActionMsg(err.message),
  });

  if (kanjiQuery.isLoading) {
    return (
      <div className="max-w-3xl mx-auto space-y-4">
        <Skeleton className="h-5 w-16" />
        <Skeleton className="h-36 w-full rounded-xl" />
        <Skeleton className="h-10 w-40" />
      </div>
    );
  }
  if (!kanji) {
    return (
      <div className="space-y-3 text-center py-10">
        <p className="text-muted-foreground">漢字が見つかりません。</p>
        <Link to="/kanji" className="text-wk-kanji font-bold">← 漢字一覧へ戻る</Link>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <Button variant="ghost" size="sm" onClick={() => navigate(-1)} className="text-muted-foreground -ml-2">
        <ArrowLeft className="size-4" />
        戻る
      </Button>

      {/* Hero */}
      <Card className="flex flex-row items-center gap-5 p-6">
        <GlyphCell type="kanji" character={kanji.character} srsStage={currentStage} size="lg" />
        <div className="min-w-0">
          <h1 className="text-3xl font-bold">{kanji.meanings[0]}</h1>
          {kanji.meanings.length > 1 && (
            <p className="text-muted-foreground">{kanji.meanings.slice(1).join(', ')}</p>
          )}
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            {kanji.frequency && <span>頻度#{kanji.frequency}</span>}
            {kanji.grade && <span>{kanji.grade}年生</span>}
            {kanji.jlpt_level && <span>JLPT N{kanji.jlpt_level}</span>}
            {kanji.stroke_count && <span>{kanji.stroke_count}画</span>}
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
          <Button onClick={() => setConfirmResurrect(true)}
            className="border border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20 hover:text-destructive">
            復活
          </Button>
        )}
        {alreadyLearned && !confirmUnlearn && (
          <Button variant="outline" onClick={() => setConfirmUnlearn(true)}>
            学習を取り消す
          </Button>
        )}
        {confirmResurrect && (
          <span className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">{kanji.character}を見習いIに復活しますか？</span>
            <Button size="sm" onClick={() => resurrectMutation.mutate()} disabled={resurrectMutation.isPending}
              className="border border-destructive/40 bg-destructive/10 text-destructive hover:bg-destructive/20 hover:text-destructive">はい</Button>
            <Button size="sm" variant="outline" onClick={() => setConfirmResurrect(false)}>キャンセル</Button>
          </span>
        )}
        {confirmUnlearn && (
          <span className="flex items-center gap-2 text-sm">
            <span className="text-destructive">{kanji.character}の学習を取り消しますか？進捗と復習が削除されます。</span>
            <Button size="sm" variant="destructive" onClick={() => unlearnMutation.mutate()} disabled={unlearnMutation.isPending}>はい</Button>
            <Button size="sm" variant="outline" onClick={() => setConfirmUnlearn(false)}>キャンセル</Button>
          </span>
        )}
      </div>
      {actionMsg && (
        <p className={`text-sm ${actionMsg.includes('！') ? 'text-success' : 'text-destructive'}`}>{actionMsg}</p>
      )}

      {/* Radicals */}
      {kanji.components && kanji.components.length > 0 && (
        <Section title="部首の組み合わせ">
          <RadicalList components={kanji.components} size="sm" />
        </Section>
      )}

      {/* Meaning */}
      <Section title="意味">
        <p className="text-lg">{kanji.meanings.join(', ')}</p>
      </Section>

      {/* Readings */}
      <Section title="読み">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground text-xs block mb-0.5">音読み</span>
            <span lang="ja" className="text-lg">
              {kanji.readings_on.map(katakanaToHiragana).join('、') || 'なし'}
            </span>
          </div>
          <div>
            <span className="text-muted-foreground text-xs block mb-0.5">訓読み</span>
            <span lang="ja" className="text-lg">{kanji.readings_kun.join('、') || 'なし'}</span>
          </div>
        </div>
      </Section>

      {/* Found in Vocabulary */}
      <Section title="この漢字を含む語彙">
        {foundIn.isLoading ? (
          <p className="text-sm text-muted-foreground animate-pulse">読み込み中…</p>
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
          <p className="text-sm text-muted-foreground">この漢字を使う語彙はまだありません。</p>
        )}
      </Section>

      <ProgressionSection itemType="kanji" itemId={kanji.id} />
    </div>
  );
}
