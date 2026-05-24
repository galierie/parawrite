import { InputRule, mergeAttributes, Node, PasteRule, type ExtendedRegExpMatchArray, type Range } from '@tiptap/core';
import { EditorState } from '@tiptap/pm/state';
import { number, parse, record, string, type InferOutput } from 'valibot';

const tag = 'span';
const group = 'inline';

const ScoreSchema = record(string(), number());
type Score = InferOutput<typeof ScoreSchema>;

/**
 * SynonymGroupNode has two options:
 *   id: identifies which <span> contains the synonym group
 *   rankings: contains the results from the model API call
 */
interface SynonymGroupOptions {
  id: string;
  scores: Score;
  HTMLAttributes: {
    class?: string;
  };
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

  // Escape via a space outside the node
  tr.insertText(' ', range.from + node.nodeSize);

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
      scores: {},
      HTMLAttributes: {},
    };
  },

  parseHTML() {
    return [
      {
        tag: `${tag}[data-synonym-group]`,
        getAttrs: (element: HTMLSpanElement) => {
          // Parse scores
          const scoresStr = element.getAttribute('data-scores');
          const scores = parse(ScoreSchema, JSON.parse(JSON.stringify(scoresStr)));

          return {
            id: element.getAttribute('data-id'),
            scores,
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
        this.options.HTMLAttributes,
        {
          'data-synonym-group': true,
          'data-id': this.options.id,
          'data-scores': JSON.stringify(this.options.scores),
        },
      ),
      0,
    ];
  },
});

/**
 * Formats the synonym groups into lists.
 */
export function getSynonymGroups(doc: EditorState['doc']) {
  const synonymGroups: Array<Array<string>> = [];
  const finalText: Array<string> = [];

  doc.descendants((node) => {
    if (node.type.name === 'synonymGroup') {
      const synonymGroupStr = node.textContent as string;

      // Treat as text if invalid node
      if (!synonymGroupStr.includes('|'))
        finalText.push(synonymGroupStr);

      const synonymGroup = synonymGroupStr
        .split('|')
        .map((word) => (word.trim()))
        .filter(Boolean);

      synonymGroups.push(synonymGroup);
      finalText.push('[MASK]');

      return false;
    } else if (typeof node.text !== 'undefined') {
      finalText.push(node.text);
    }

    return true;
  });

  return { synonymGroups, finalText: finalText.join(' ') };
}