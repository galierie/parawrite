import { EditorState } from '@tiptap/pm/state';
import {
    type ExtendedRegExpMatchArray,
    InputRule,
    mergeAttributes,
    Node,
    PasteRule,
    type Range,
} from '@tiptap/core';
import { number, parse, record, string } from 'valibot';

const tag = 'span';
const group = 'inline';

const ScoreSchema = record(string(), number());

const ReasonSchema = record(string(), number());

// eslint-disable-next-line prefer-named-capture-group -- no
const synonymGroupPattern: RegExp = /([\w-]+(?:\|[\w-]+)+)/u;
function replaceWithSynonymGroup({
    state,
    range,
    match,
}: {
    state: EditorState;
    range: Range;
    match: ExtendedRegExpMatchArray;
}) {
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

    const { tr } = state;
    tr.replaceWith(range.from, range.to, node);

    // Escape via a space outside the node
    tr.insertText(' ', range.from + node.nodeSize);

    // Reinsert the missing whitespace as well
    if (range.from !== 1) tr.insertText(' ', range.from);
}

/**
 * SynonymGroupNode contains the entire synonym group and stores the following:
 *   id: identifies which <span> contains the synonym group
 *   scores: contains the scores from the model API call
 *   reasons: contains the reasons from the model API call
 */
export const SynonymGroupNode = Node.create({
    name: 'synonymGroup',

    group,
    inline: group === 'inline',

    atom: false,
    content: 'text*',
    selectable: true,

    addAttributes() {
        return {
            id: {
                default: crypto.randomUUID(),
                parseHTML: (element) => element.getAttribute('data-id'),
                renderHTML: (attrs) => ({ 'data-id': attrs.id }),
            },
            scores: {
                default: {},
                parseHTML(element) {
                    const scoresStr = element.getAttribute('data-scores');
                    const scores = parse(ScoreSchema, JSON.parse(JSON.stringify(scoresStr)));
                    return scores;
                },
                renderHTML: (attrs) => ({ 'data-scores': JSON.stringify(attrs.scores) }),
            },
            reasons: {
                default: {},
                parseHTML(element) {
                    const reasonsStr = element.getAttribute('data-reasons');
                    const reasons = parse(ReasonSchema, JSON.parse(JSON.stringify(reasonsStr)));
                    return reasons;
                },
                renderHTML: (attrs) => ({ 'data-reasons': JSON.stringify(attrs.reasons) }),
            },
        };
    },

    addInputRules() {
        return [
            new InputRule({
                find: new RegExp(`(^|\\s)${synonymGroupPattern.source}\\s$`, 'u'),
                handler: replaceWithSynonymGroup,
            }),
        ];
    },

    addPasteRules() {
        return [
            new PasteRule({
                find: new RegExp(synonymGroupPattern.source, 'gu'),
                handler: replaceWithSynonymGroup,
            }),
        ];
    },

    addOptions() {
        return {
            HTMLAttributes: {},
        };
    },

    parseHTML() {
        return [
            {
                tag: `${tag}[data-synonym-group]`,
            },
        ];
    },

    renderHTML({ HTMLAttributes }) {
        return [
            tag,
            mergeAttributes(HTMLAttributes, this.options.HTMLAttributes, {
                'data-synonym-group': true,
            }),
            0,
        ];
    },
});

/**
 * Formats the synonym groups into lists.
 */
export function getSynonymGroups(doc: EditorState['doc']) {
    const synonymGroups: Array<{ id: string; words: Array<string> }> = [];
    const finalText: Array<string> = [];

    doc.descendants((node) => {
        if (node.type.name === 'synonymGroup') {
            const synonymGroupStr = node.textContent as string;

            // Treat as text if invalid node
            if (!synonymGroupStr.includes('|')) finalText.push(synonymGroupStr);

            const words = synonymGroupStr
                .split('|')
                .map((word) => word.trim())
                .filter(Boolean);

            synonymGroups.push({ id: node.attrs.id, words });
            finalText.push('[MASK]');

            return false;
        } else if (typeof node.text !== 'undefined') {
            finalText.push(node.text);
        }

        return true;
    });

    return { synonymGroups, finalText: finalText.join(' ') };
}
