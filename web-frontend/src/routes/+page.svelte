<script lang="ts">
    import Icon from '@iconify/svelte';
    import { EditorState } from '@tiptap/pm/state';
    import { EditorView } from '@tiptap/pm/view';
    import { onDestroy, onMount } from 'svelte';
    import { parse } from 'valibot';

    import { enhance } from '$app/forms';
    import { getSynonymGroups } from '$lib/features/text-editor/extensions';
    import { PUBLIC_API_URL_WS } from '$env/static/public';
    import { type Response, ResponseSchema } from '$lib/models';
    import { TextEditorComponent } from '$lib/features/text-editor';

    let edState: EditorState = $state({} as EditorState);
    let view: EditorView = $state({} as EditorView);

    let ws: WebSocket | null = $state(null);

    let startTime: DOMHighResTimeStamp | null = $state(null);
    let endTime: DOMHighResTimeStamp | null = $state(null);

    let canRate = $state(false);
    let hasRated = $state(false);
    let showForm = $state(false);

    function initWebSocket() {
        if (ws !== null) ws.close();

        ws = new WebSocket(`${PUBLIC_API_URL_WS}/recommend`);

        ws.onopen = () => {
            console.log('WebSocket open!');
        };

        ws.onmessage = (ev) => {
            // Receive results
            try {
                const data: Response = parse(ResponseSchema, JSON.parse(ev.data));

                if (data.status === 200) {
                    const { selection, tr } = edState;

                    // For each group,
                    data.synonym_group_results.forEach(({ id, results }) => {
                        // Map each word to their score and reason
                        const scores: Record<string, number> = {};
                        const reasons: Record<string, string> = {};
                        results.forEach(({ word, score, reason }) => {
                            scores[word] = score;
                            reasons[word] = reason;
                        });

                        // Fill-in data-scores and data-reasons
                        // Bahala na si SynonymGroupNode to convert these into UI
                        edState.doc.descendants((node, pos) => {
                            // Look for the node with the group.id
                            if (node.type.name === 'synonymGroup' && node.attrs.id === id) {
                                // Fill-in data-scores and data-reasons
                                // eslint-disable-next-line no-undefined -- needed for function
                                tr.setNodeMarkup(pos, undefined, {
                                    ...node.attrs,
                                    scores,
                                    reasons,
                                });
                                return false;
                            }

                            return true;
                        });
                    });

                    if (tr.docChanged) {
                        // Preserve current selection
                        tr.setSelection(selection.map(tr.doc, tr.mapping));

                        // Dispatch transaction
                        view.dispatch(tr);

                        if (startTime !== null) {
                            endTime = performance.now();
                            console.log(`Average Latency: ${(endTime - startTime) / 1000}`);
                        }
                    }
                } else {
                    throw Error(`${data.status}: ${data.message}`);
                }
            } catch (err) {
                console.error(
                    `WebSocket error: ${err instanceof Error ? err.message : 'Unknown error'}`,
                );
            }
        };

        ws.onclose = () => {
            console.log('WebSocket closed.');
        };

        ws.onerror = (ev) => {
            console.error('WebSocket error:', ev);
        };
    }

    function sendToModel() {
        startTime = performance.now();
        if (ws !== null && ws.OPEN) {
            const { synonymGroups, finalText } = getSynonymGroups(edState.doc);
            ws.send(
                JSON.stringify({
                    synonym_groups: synonymGroups,
                    text: finalText,
                }),
            );
            if (!canRate) canRate = true;
        }
    }

    onMount(() => {
        // Create WebSocket connection
        initWebSocket();

        // Every now and then, send data via the WebSocket
        setInterval(sendToModel, 500);
    });

    onDestroy(() => {
        // Destroy WebSocket connection
        if (ws !== null) ws.close();
    });
</script>

<div class="mb-24 text-center text-grandis-100">
    <h1 class="font-satisfy text-6xl sm:text-8xl">Parawrite</h1>
    <p class="text-base sm:text-xl">Your personal writing companion</p>
</div>

<div class="flex justify-center">
    <div
        class="relative min-h-[297mm] w-[210mm] bg-white p-6 text-black shadow-lg shadow-black sm:p-12 lg:p-24"
    >
        <TextEditorComponent bind:edState bind:view />
    </div>
</div>

{#if canRate && !hasRated}
    <button
        type="button"
        class="fixed bottom-10 right-10 rounded-lg shadow-lg bg-white"
        onclick={() => (showForm = true)}
    >
        <Icon icon="tabler:thumb-up" class="h-12 w-12 p-2" />
    </button>

    {#if showForm}
        <div
            class="fixed top-0 left-0 h-screen w-screen flex items-center justify-center z-100 bg-black/80"
        >
            <form
                method="POST"
                action="?/rate"
                class="bg-white rounded-lg h-[60%] w-[80%] flex items-center justify-center"
                use:enhance
            >
                <button
                    type="button"
                    class="absolute top-15 right-15 rounded-full bg-red-500 text-white"
                    onclick={() => (showForm = false)}
                >
                    <Icon icon="tabler:x" class="h-12 w-12 p-2" />
                </button>

                <div class="h-full w-full flex flex-col items-center justify-center">
                    <p class="text-center mb-4 text-2xl">Rate our website!</p>

                    <div class="flex items-center justify-center gap-4">
                        <label class="flex flex-col justify-center items-center">
                            <input type="radio" name="rating" value="1" />
                            <span>1 (Wow it's bad)</span>
                        </label>

                        <label class="flex flex-col justify-center items-center">
                            <input type="radio" name="rating" value="2" />
                            <span>2</span>
                        </label>

                        <label class="flex flex-col justify-center items-center">
                            <input type="radio" name="rating" value="3" />
                            <span>3</span>
                        </label>

                        <label class="flex flex-col justify-center items-center">
                            <input type="radio" name="rating" value="4" />
                            <span>4</span>
                        </label>

                        <label class="flex flex-col justify-center items-center">
                            <input type="radio" name="rating" value="5" />
                            <span>5 (Wow it's great)</span>
                        </label>
                    </div>

                    <button
                        type="submit"
                        class="mt-20 bg-green-500 text-white rounded-lg px-4 py-2"
                        onclick={() => {
                            showForm = false;
                            hasRated = true;
                        }}>Submit!</button
                    >
                </div>
            </form>
        </div>
    {/if}
{/if}
