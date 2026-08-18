import type { AnalyzedItem } from "../types";
import { publishedMs } from "./filters";

/** Un groupe d'un seul item est un item autonome ; un groupe de plusieurs est un fil. Le composant
 *  de rendu décide comment traiter chaque cas — cette fonction ne fait que regrouper. */
export type ThreadGroup = AnalyzedItem[];

/** Regroupe une liste déjà filtrée/triée par `thread_id`, sans changer l'ordre relatif : un groupe
 *  apparaît à la position de son premier item rencontré, les occurrences suivantes du même
 *  `thread_id` s'y ajoutent plutôt que de créer une nouvelle entrée plus loin dans la liste. Un
 *  item sans `thread_id` reste seul — ce n'est pas un fil de taille 1, il n'a jamais été rapproché
 *  d'un autre dossier.
 *
 *  Chaque groupe de plusieurs items est ensuite trié par ordre chronologique croissant, quel que
 *  soit le critère de tri global (confiance, catégorie…) qui a déterminé la position du groupe
 *  lui-même : c'est ce qui fait du fil un « fil chronologique » plutôt qu'un simple paquet
 *  d'articles liés. */
export function groupThreads(items: AnalyzedItem[]): ThreadGroup[] {
  const groups: ThreadGroup[] = [];
  const indexByThreadId = new Map<string, number>();

  for (const item of items) {
    const threadId = item.thread_id;
    if (!threadId) {
      groups.push([item]);
      continue;
    }
    const existing = indexByThreadId.get(threadId);
    if (existing === undefined) {
      indexByThreadId.set(threadId, groups.length);
      groups.push([item]);
    } else {
      groups[existing].push(item);
    }
  }

  for (const group of groups) {
    if (group.length > 1) group.sort((a, b) => publishedMs(a) - publishedMs(b));
  }

  return groups;
}
