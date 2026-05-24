<script lang="ts">
    import Icon from '@iconify/svelte';
    import TextAlign from '@tiptap/extension-text-align';
    import { Editor } from '@tiptap/core';
    import { EditorState } from '@tiptap/pm/state';
    import { EditorView } from '@tiptap/pm/view';
    import { onDestroy, onMount } from 'svelte';
    import { StarterKit, type StarterKitOptions } from '@tiptap/starter-kit';

    import { CtrlKLink, setLink, SynonymGroupNode } from './extensions';
    
    interface Props {
        edState: EditorState;
        view: EditorView;
    }

    let { edState = $bindable(), view = $bindable() }: Props = $props();

    let editorState: { editor: Editor | null } = $state({ editor: null });
    let editorElement: HTMLDivElement | null = $state(null);

    const starterKitExtensionsConfig: Partial<StarterKitOptions> = {
        blockquote: false,
        bulletList: {
            HTMLAttributes: {
                class: 'list-disc pl-6',
            },
        },
        dropcursor: false,
        horizontalRule: false,
        link: false,
        orderedList: {
            HTMLAttributes: {
                class: 'list-decimal pl-6',
            },
        },
    };

    function mountEditor() {
        editorState.editor = new Editor({
            element: editorElement,
            extensions: [
                StarterKit.configure(starterKitExtensionsConfig),
                CtrlKLink.configure({
                    HTMLAttributes: {
                        class: 'underline',
                    },
                }),
                TextAlign.configure({
                    types: ['paragraph'],
                    defaultAlignment: 'left',
                }),
                SynonymGroupNode.configure({
                    HTMLAttributes: {
                        class: 'bg-grandis-100',
                    },
                }),
            ],
            editorProps: {
                attributes: {
                    class: 'focus:outline-none focus:ring-0 h-full w-full',
                },
            },
            onTransaction({ editor }) {
                // Update the state signal to force a re-render
                editorState = { editor };
            },
            onUpdate({ editor }) {
                // No initial content naman, so this should work
                edState = editor.state;
                view = editor.view;
            }
        });
    }

    onMount(() => {
        if (editorElement !== null) mountEditor();
    });

    onDestroy(() => {
        if (editorState.editor !== null) editorState.editor.destroy();
    });
</script>

{#snippet formatBtn(tablerIcon: string, onclick: () => void)}
    <button {onclick} class="mx-2">
        <Icon icon={`tabler:${tablerIcon}`} class="h-5 w-5" />
    </button>
{/snippet}

<div class="relative h-full w-full">
    {#if editorState.editor}
        {@const { editor } = editorState}

        <div class="flex justify-center items-center">
            <div
                class="flex justify-center items-center relative -top-7 h-7 w-fit shadow-sm rounded-sm"
            >
                {@render formatBtn('arrow-back-up', () => editor.chain().focus().undo().run())}
                {@render formatBtn('arrow-forward-up', () => editor.chain().focus().redo().run())}
                <Icon icon="tabler:minus-vertical" class="text-gray-400 h-6 w-6" />
                {@render formatBtn('bold', () => editor.chain().focus().toggleBold().run())}
                {@render formatBtn('italic', () => editor.chain().focus().toggleItalic().run())}
                {@render formatBtn('underline', () =>
                    editor.chain().focus().toggleUnderline().run(),
                )}
                {@render formatBtn('strikethrough', () =>
                    editor.chain().focus().toggleStrike().run(),
                )}
                <Icon icon="tabler:minus-vertical" class="text-gray-400 h-6 w-6" />
                {@render formatBtn('code', () => editor.chain().focus().toggleCode().run())}
                {@render formatBtn('link', () => setLink(editor))}
                <Icon icon="tabler:minus-vertical" class="text-gray-400 h-6 w-6" />
                {@render formatBtn('list', () => editor.chain().focus().toggleBulletList().run())}
                {@render formatBtn('list-numbers', () =>
                    editor.chain().focus().toggleOrderedList().run(),
                )}
                <Icon icon="tabler:minus-vertical" class="text-gray-400 h-6 w-6" />
                {@render formatBtn('align-left', () =>
                    editor.chain().focus().setTextAlign('left').run(),
                )}
                {@render formatBtn('align-center', () =>
                    editor.chain().focus().setTextAlign('center').run(),
                )}
                {@render formatBtn('align-right', () =>
                    editor.chain().focus().setTextAlign('right').run(),
                )}
                {@render formatBtn('align-justified', () =>
                    editor.chain().focus().setTextAlign('justify').run(),
                )}
            </div>
        </div>
    {/if}
    <div class="h-full w-full" bind:this={editorElement}></div>
</div>
