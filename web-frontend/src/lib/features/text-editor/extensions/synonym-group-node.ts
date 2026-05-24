import { InputRule, mergeAttributes, Node, PasteRule, type ExtendedRegExpMatchArray, type Range } from '@tiptap/core';
import { EditorState } from '@tiptap/pm/state';
import { number, parse, record, string, type InferOutput } from 'valibot';

const tag = 'span';
const group = 'inline';

const RankingSchema = record(string(), number());
type Ranking = InferOutput<typeof RankingSchema>;

/**
 * SynonymGroupNode has two options:
 *   id: identifies which <span> contains the synonym group
 *   rankings: contains the results from the model API call
 */
interface SynonymGroupOptions {
  id: string;
  rankings: Ranking;
}

const synonymGroupPattern: RegExp = /([\w-]+(?:\|[\w-]+)+)/;
function replaceWithSynonymGroup({ state, range, match }: { state: EditorState, range: Range, match: ExtendedRegExpMatchArray }) {
  if (range.from < 0) return;

  // Prevent refire
  let hasGroup = false;
  state.doc.nodesBetween(range.from, range.to, (node) => {
    if (node.type.name === 'synonymGroup') {
      hasGroup = true;
      return false; // Stop iterating once found
    }
  });
  if (hasGroup) return;

  // Make a node with the captured text
  const content = match[2] ?? match[1];
  const node = state.schema.nodes.synonymGroup.create({}, state.schema.text(content));
  
  const tr = state.tr;
  tr.replaceWith(range.from, range.to, node);

  // Reinsert a space inside AND outside the node
  tr.insertText(' ', range.from + node.nodeSize);
  tr.insertText(' ', range.from + node.nodeSize - 1);

  // Reinsert the missing whitespace as well
  if (range.from !== 1)
    tr.insertText(' ', range.from);

  return;
}

/**
 * SynonymGroupNode contains the entire synonym group.
 */
export const SynonymGroupNode = Node.create<SynonymGroupOptions>({
  name: 'synonymGroup',

  group,
  inline: group == 'inline',

  atom: false,
  content: 'text*',
  selectable: true,

  addInputRules() {
    return [
      new InputRule({
        find: new RegExp(`(^|\\s)${synonymGroupPattern.source}\\s$`),
        handler: replaceWithSynonymGroup,
      }),
    ];
  },

  addPasteRules() {
    return [
      new PasteRule({
        find: new RegExp(synonymGroupPattern.source, 'g'),
        handler: replaceWithSynonymGroup,
      }),
    ];
  },

  addOptions() {
    return {
      id: crypto.randomUUID(),
      rankings: {},
    };
  },

  parseHTML() {
    return [
      {
        tag: `${tag}[data-synonym-group]`,
        getAttrs: (element: HTMLSpanElement) => {
          // Parse rankings
          const rankingsStr = element.getAttribute('data-rankings');
          const rankings = parse(RankingSchema, JSON.parse(JSON.stringify(rankingsStr)));

          return {
            id: element.getAttribute('data-id'),
            rankings,
          }
        }
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      tag,
      mergeAttributes(
        HTMLAttributes,
        {
          'data-synonym-group': true,
          'data-id': this.options.id,
          'data-rankings': JSON.stringify(this.options.rankings),
        },
      ),
      0,
    ];
  },
})