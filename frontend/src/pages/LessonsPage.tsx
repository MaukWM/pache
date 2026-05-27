import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type QueueItem } from '../lib/api';

export function LessonsPage() {
  const queryClient = useQueryClient();

  const queue = useQuery({
    queryKey: ['queue'],
    queryFn: api.getQueue,
  });

  const completeMutation = useMutation({
    mutationFn: api.completeLessons,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      queryClient.invalidateQueries({ queryKey: ['progress'] });
      queryClient.invalidateQueries({ queryKey: ['reviews'] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: ({ item_type, item_id }: { item_type: string; item_id: number }) =>
      api.removeFromQueue(item_type, item_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue'] });
    },
  });

  const handleCompleteAll = () => {
    if (!queue.data?.length) return;
    const item_ids = queue.data.map((q: QueueItem) => ({
      item_type: q.item_type,
      item_id: q.item_id,
    }));
    completeMutation.mutate({ item_ids });
  };

  const handleCompleteOne = (item: QueueItem) => {
    completeMutation.mutate({
      item_ids: [{ item_type: item.item_type, item_id: item.item_id }],
    });
  };

  const items = queue.data || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Lesson Queue</h1>
        {items.length > 0 && (
          <button
            onClick={handleCompleteAll}
            disabled={completeMutation.isPending}
            className="px-4 py-2 rounded-lg bg-wk-radical text-white font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {completeMutation.isPending ? 'Starting...' : `Start All ${items.length} Lessons`}
          </button>
        )}
      </div>

      {queue.isLoading ? (
        <div className="text-text-muted animate-pulse">Loading queue...</div>
      ) : items.length === 0 ? (
        <div className="bg-surface rounded-xl p-10 text-center">
          <div className="text-4xl mb-3">&#128218;</div>
          <h2 className="text-xl font-bold">No lessons queued</h2>
          <p className="text-text-muted mt-2">
            Browse the vocab pool and add items to your lesson queue to get started.
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {items.map((item) => {
            const isKanji = item.item_type === 'kanji';
            const display = item.item_details?.character || item.item_details?.word || '?';
            const bgColor = isKanji ? 'bg-wk-kanji' : 'bg-wk-vocab';

            return (
              <div
                key={`${item.item_type}-${item.item_id}`}
                className="bg-surface rounded-xl p-4 shadow-sm flex items-center gap-4"
              >
                <div
                  className={`${bgColor} w-14 h-14 rounded-lg flex items-center justify-center text-white font-bold text-xl shrink-0`}
                >
                  {display}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-bold">{display}</div>
                  <div className="text-sm text-text-muted">
                    {item.item_details?.meanings?.join(', ') || item.item_type}
                  </div>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => handleCompleteOne(item)}
                    disabled={completeMutation.isPending}
                    className="px-3 py-1.5 rounded-lg bg-wk-radical text-white text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    Learn
                  </button>
                  <button
                    onClick={() =>
                      removeMutation.mutate({
                        item_type: item.item_type,
                        item_id: item.item_id,
                      })
                    }
                    disabled={removeMutation.isPending}
                    className="px-3 py-1.5 rounded-lg bg-border text-text-muted text-sm font-bold hover:bg-error hover:text-white transition-colors disabled:opacity-50"
                  >
                    Remove
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
