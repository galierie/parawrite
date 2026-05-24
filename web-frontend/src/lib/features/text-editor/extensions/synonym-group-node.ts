import { InputRule, mergeAttributes, Node } from '@tiptap/core';
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
        find: /(?:^|\s)([\w-]+(?:\|[\w-]+)+)\s$/,
        handler: ({ state, range, match }) => {
          const content = match[1];

          // Make a node with the captured text
          const node = state.schema.nodes.synonymGroupNode.create({}, state.schema.text(content));
          
          // Limit range to that of captured text
          const from = range.to - content.length - 1;
          const to = range.from + content.length;

          state.tr.replaceRangeWith(from, to, node);
        },
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