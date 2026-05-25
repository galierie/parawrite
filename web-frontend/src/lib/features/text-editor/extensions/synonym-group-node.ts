import { Decoration, DecorationSet } from '@tiptap/pm/view';
import { EditorState, Plugin, PluginKey } from '@tiptap/pm/state';
import {
    type ExtendedRegExpMatchArray,
    Extension,
    InputRule,
    mergeAttributes,
    Node,
    PasteRule,
    type Range,
} from '@tiptap/core';
import { type InferOutput, number, parse, record, string } from 'valibot';

const tag = 'span';
const group = 'inline';

const ScoreSchema = record(string(), number());
type Score = InferOutput<typeof ScoreSchema>;

const ReasonSchema = record(string(), string());
type Reason = InferOutput<typeof ReasonSchema>;

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
                default: null,
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

export const SynonymDecorator = Extension.create({
    name: 'synonymDecorator',

    addProseMirrorPlugins() {
        return [
            new Plugin({
                key: new PluginKey('synonym-decorator'),
                state: {
                    init: (_, { doc }) => {
                        return this.options.decorateSynonyms(doc);
                    },
                    apply: (tr, prev) => {
                        return tr.docChanged
                            ? this.options.decorateSynonyms(tr.doc)
                            : prev.map(tr.mapping, tr.doc);
                    },
                },
                props: {
                    decorations(state) {
                        return this.getState(state);
                    },
                },
            }),
        ];
    },

    addOptions() {
        return {
            decorateSynonyms(doc: EditorState['doc']) {
                const decorations: Decoration[] = [];

                doc.descendants((node, pos) => {
                    if (node.type.name === 'synonymGroup') {
                        const scores = node.attrs.scores as Score;
                        if (Object.keys(scores).length === 0) return false;

                        const reasons = node.attrs.reasons as Reason;
                        if (Object.keys(reasons).length === 0) return false;

                        const text = node.textContent;

                        // Get the highest score
                        const highestScore = Math.max(...Object.values(scores));

                        let posOffset = 0;

                        text.split('|').forEach((rawStr) => {
                            const word = rawStr.trim();

                            // Get the synonym score
                            const score = scores[word];
                            if (score === null) return;

                            // Get the synonym reason
                            const reason = reasons[word];
                            if (reason === null) return;

                            // Highlight the entire string in the middle of two pipes
                            const from = pos + 1 + posOffset;
                            const to = from + rawStr.length;

                            decorations.push(
                                Decoration.inline(from, to, {
                                    class: score === highestScore ? 'bg-my-sin' : 'bg-mandalay',
                                    title: reason,
                                }),
                            );

                            posOffset += rawStr.length + 1;
                        });

                        return false;
                    }

                    return true;
                });

                return DecorationSet.create(doc, decorations);
            },
        };
    },
});
