<script lang="ts">
    import { TextEditorComponent } from '$lib/features/text-editor';
</script>

<div class="mb-24 text-center text-grandis-100">
    <h1 class="font-satisfy text-6xl sm:text-8xl">Parawrite</h1>
    <p class="text-base sm:text-xl">Your personal writing companion</p>
</div>

<div class="flex justify-center">
    <div
        class="grid min-h-[297mm] w-[210mm] grid-cols-1 bg-white p-6 text-black shadow-lg shadow-black sm:p-12 lg:p-24"
    >
        <TextEditorComponent />
    </div>
</div>
