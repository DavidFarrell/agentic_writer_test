# Specification: Context-managed AI-assisted Blogging Tool

## 1. Purpose and goals

### 1.1 Purpose
Build a local-first web application that helps the user draft blog posts using large language models (LLMs) without producing generic "AI slop". The app must:

- Treat the human as the primary author.
- Use AI to assist with structure, style and detail, not to overwrite the author’s intent.
- Give the user explicit, fine-grained control over what context the AI can see at any moment.
- Support a multi-pass, agentic workflow (writer, editor, fact-checker etc.) while remaining transparent and inspectable.

### 1.2 Key outcomes

- The user can:
  - Import source materials (files and URLs, including YouTube tutorials and transcripts).
  - Import their own dictated notes / transcripts.
  - Import a corpus of their previous blog posts.
  - Select which materials are in the active context for a given AI action.
  - See a visual representation (a "GenAI map") of how much of the context window is currently used by each resource.
  - Run specialised agents (Writer, Style Editor, Detail Editor, Fact Checker etc.) on a shared artefact (the draft blog post).
  - Inspect the agents’ reasoning and changes over time.
  - Step through artefact versions (undo / redo, version history).

- The system can:
  - Use Gemini models (default Gemini 3 Pro, but configurable) with large context windows.
  - Tokenise all imported resources and track token usage against the selected model’s context limits.
  - Dynamically include / exclude resources from context based on user selection and token budget.
  - Automatically summarise or sample over-long resources when needed, while keeping this visible and under user control.


## 2. Constraints and technology choices

### 2.1 Language and framework

- All application code must be written in Python.
- Use FastHTML as the server framework.
- Use Munster UI (ShadCN-based) for the UI component system.

### 2.2 LLMs and model provider

- Primary model family: Google Gemini.
- Must support, at minimum:
  - Gemini 3 Pro (default for main chat and agents).
  - Gemini 2.5 Pro.
  - Gemini 2.5 Flash.
  - Gemini 2.5 Flash-lite (if available in APIs).
- The model choice must be user-selectable at runtime via a dropdown in the UI.
- The application must read model capabilities dynamically where possible (context window size, supported modalities etc.), rather than hard-coding.

### 2.3 Repository structure and documentation

- The repository will contain a folder `LLM_docs/` with design notes and documentation about LLM usage.
- **Mandatory rule:** any autonomous agent or code-generation routine used to extend or modify this application must first load and read all documents in `LLM_docs/` before writing any code.
  - Implement this as a clear developer contract in code comments and as part of any orchestration scripts (for example an internal “dev assistant” agent).
  - Where agents are used in the runtime system (e.g. Writer, Style Editor), they do not need `LLM_docs` but any development-focused agents do.


## 3. User roles and primary workflows

### 3.1 Roles

- **Author (primary user):** a technically literate writer who understands LLMs, context windows, and wants fine-grained control.
- No separate admin role is required initially.

### 3.2 Core workflows

1. **Start a new writing project**
   - User creates a new “Project” (e.g. “Blog post about X YouTube tutorial”).
   - User selects default model (e.g. Gemini 3 Pro).
   - System displays an empty context map and empty artefact panel.

2. **Import resources**
   - User uploads files from local disk:
     - Supported initial formats: `\.txt`, `\.md`, `\.pdf`, `\.docx`, `\.html`, `\.json`, common image formats (e\.g\. `\.png`, `\.jpg`, `\.webp`), common video formats (e\.g\. `\.mp4`, `\.mov`), and common audio formats (e\.g\. `\.wav`, `\.mp3`, `\.m4a`). Non-text formats are ingested by extracting text via captions or transcripts so that they can also be tokenised.
     - System stores the raw file and extracts text content for tokenisation.
   - User adds URLs:
     - For standard web pages: system fetches HTML, extracts main content, and stores text in markdown format.
     - For YouTube links: system uses Gemini multimodal or a dedicated transcript pipeline (e.g. YouTube APIs or model-based speech-to-text using Gemini 2.5 Flash by default) to obtain a transcript. The specific Gemini model used for transcription is configurable by the user, with 2.5 Flash as the default choice.
   - User can explicitly label resources (e.g. “My audio notes”, “Source video transcript”, “Original article”, “My past blog corpus”). On ingestion, the system proposes a sensible default label based on filename, page title or URL, which the user can then edit.

3. **Context inspection and management**
   - System tokenises each resource using the tokeniser appropriate for the currently selected model.
   - System shows a context visualisation (treemap-style) sized relative to the model’s maximum context.
   - Each resource is a coloured rectangle representing its token footprint. Colour encodes resource type (notes, source, corpus, other).
   - The user can:
     - Toggle each resource “active” / “inactive” for inclusion in the next AI call.
     - Hover to see details (name, type, token count, origin, last updated).
     - See total tokens used by the currently active set versus the model’s maximum.

4. **Drafting the artefact**
   - User uses the main chat box to issue commands like “Create a first draft based on my audio notes, using the source video transcript for detail and my corpus for style reference.”
   - Below the chat box are agent buttons (Writer, Style Editor, Detail Editor, Fact Checker etc.).
   - When the user submits, the system:
     - Gathers the currently active resources, constrained by token budget.
     - Runs the selected agent(s) against the current artefact.
     - Updates the artefact panel with the new draft or edits.
     - Records a new version in the version history.

5. **Iterative refinement**
   - The user can:
     - Ask follow-up questions in the chat.
     - Re-run one or more agents with revised instructions.
     - Change the active resource set (e.g. swap out the source book for the corpus) and re-run passes.
   - The system keeps the artefact versioned and allows undo / redo, and selective restoration of older versions.

6. **Export**
   - User can export the final artefact as:
     - Markdown (`.md`).
     - HTML snippet.
     - Plain text.
   - Optionally, provide a “copy as markdown” shortcut.


## 4. High-level architecture

### 4.1 Overview

- **Client** (browser):
  - Rendered by FastHTML + Munster UI components.
  - Provides:
    - File and URL input UI.
    - Context map visualisation.
    - Chat and agent controls.
    - Artefact editor and version history UI.
    - Agent log inspector.

- **Server** (Python + FastHTML):
  - HTTP API endpoints for:
    - Project CRUD.
    - Resource ingestion and storage.
    - Tokenisation and token accounting.
    - LLM calls for chat and agents.
    - Artefact CRUD and version history.
    - Agent log retrieval.
  - Orchestration layer for multi-pass agents.

- **Storage**
  - For a first version, use a lightweight local database (e.g. SQLite) plus filesystem storage for raw files.
  - Tables/entities:
    - `projects`
    - `resources`
    - `resource_chunks` (if chunking is needed)
    - `artefacts`
    - `artefact_versions`
    - `agent_runs`
    - `agent_run_logs`

### 4.2 Security and privacy

- Store all user content locally by default.
- Outbound calls to Gemini APIs must:
  - Only send the specific text that is currently in the selected context for that call.
  - Never upload raw files wholesale unless explicitly required.


## 5. Data model (conceptual)

### 5.1 Project

- `id`: unique identifier.
- `name`: string.
- `created_at`, `updated_at`.
- `default_model_id`: reference to a model configuration.
- `description`: optional.

### 5.2 Resource

Represents a logical item the user has added.

- `id`.
- `project_id`.
- `label`: user-facing name.
- `type`: enum, e.g. `audio_notes`, `source_transcript`, `article`, `book`, `blog_corpus`, `other`.
- `origin`: enum `file_upload`, `url`, `youtube`, `manual`.
- `raw_path`: filesystem path for stored original file, if applicable.
- `url`: original URL, if applicable.
- `total_tokens`: token count for the full resource for a given model (store per model if needed).
- `active`: boolean indicating whether it is currently included in the context (per project-session state; may be stored separately).

### 5.3 ResourceChunk (optional for v1, but design for it)

If the resource exceeds the context window or needs chunking:

- `id`.
- `resource_id`.
- `sequence_index`.
- `text`: chunk text.
- `token_count`.

### 5.4 Artefact

Represents the current working document for a project.

- `id`.
- `project_id`.
- `title`.
- `current_version_id`.

### 5.5 ArtefactVersion

- `id`.
- `artefact_id`.
- `created_at`.
- `created_by_agent`: nullable, e.g. `writer`, `style_editor`, `detail_editor`, `fact_checker`, or `user`.
- `prompt_summary`: short description of why this version exists.
- `content_markdown`: the full markdown content.

### 5.6 AgentRun and logs

- `AgentRun`:
  - `id`.
  - `project_id`.
  - `artefact_id`.
  - `agent_type` (writer, style_editor, etc.).
  - `started_at`, `completed_at`.
  - `status`: `running`, `completed`, `failed`.
  - `iteration_count`: how many passes.

- `AgentRunLog`:
  - `id`.
  - `agent_run_id`.
  - `iteration_index`.
  - `role`: `system`, `user`, `assistant`, `tool`.
  - `content`: the text exchanged.
  - `tokens_used` (if available from API).


## 6. Context ingestion and token accounting

### 6.1 Tokenisation service

Implement a central tokenisation service module:

- Responsible for:
  - Loading the appropriate tokeniser for each supported model.
  - Providing:
    - `count_tokens(text, model_id)`.
    - `max_context_tokens(model_id)`.
  - Caching results per `(resource_id, model_id)` pair to avoid repeated tokenisation.

### 6.2 Ingestion steps

For any new resource:

1. Store original input (file or fetched HTML / transcript) on disk.
2. Extract text using format-specific extractors.
3. Tokenise to get `total_tokens` for the currently selected default model.
4. If `total_tokens` > `max_context_tokens(model)`:
   - Mark the resource as `too_large_for_single_context`.
   - Optionally create `ResourceChunks` using a simple chunking algorithm based on tokens.
5. Update the context visualisation.

### 6.3 Context selection per AI call

Before any LLM call:

- Collect all resources marked `active` for the project.
- For each active resource, determine whether to include:
  - Full text.
  - Summarised version.
  - Selected chunks.
- Compose a context plan such that:
  - Sum of tokens of all included texts + prompt + artefact content < `max_context_tokens` for the selected model.
  - If the limit would be exceeded, apply a deterministic strategy (for example):
    1. Always prioritise user’s audio notes and current artefact.
    2. Next prioritise source materials.
    3. Then prioritise style corpus.
    4. When needed, fall back to summarised versions.
- Store this context plan in the `AgentRunLog` for transparency.


## 7. Context visualisation (treemap)

### 7.1 Goals

- Present a clear, visual map of how the context window is allocated.
- Make it easy to see which resources are “expensive” in token terms.
- Allow toggling of resources directly from the visualisation.

### 7.2 Behaviour

- For the selected model:
  - The treemap rectangle represents `max_context_tokens(model)`.
  - Each resource is a sub-rectangle sized proportionally to `total_tokens`.
  - Colour encodes `type` (e.g. notes, source, corpus, other).
  - Resources with `too_large_for_single_context` are flagged, e.g. outlined or hatched, and represent their full size even if chunking is used.
- User interactions:
  - Click on a rectangle toggles `active` on / off. Active resources appear with normal shading; inactive resources appear visually distinct (for example slightly darkened or desaturated) to indicate they are not currently in the context.
  - Hover shows tooltip with detailed metadata.
  - A side panel lists resources with checkboxes, mirroring the treemap state.


## 8. Chat, agent controls and artefact panel

### 8.1 Layout

A suggested three-panel layout for desktop screens:

- **Left panel:** Resources and context map
  - Treemap visualisation.
  - Resource list with toggles and quick filters.

- **Centre panel:** Main chat and agent controls
  - Model selector dropdown (default Gemini 3 Pro).
  - Chat transcript (user and assistant messages).
  - Prompt input box.
  - Buttons beneath prompt:
    - `Run as plain chat`.
    - `Run Writer agent`.
    - `Run Style Editor`.
    - `Run Detail Editor`.
    - `Run Fact Checker`.
    - Potential future agents can be added here.

- **Right panel:** Artefact and versions
  - Markdown-rendering editor for the current artefact.
  - Controls:
    - Edit inline (user edits are allowed).
    - Save user edits as a new version.
    - Undo / redo within current editing session.
  - Version history list:
    - Timeline showing versions with timestamp, agent type, and short description.
    - Clicking a version loads it into the editor.
    - Option to compare two versions (diff view) is a stretch goal.

### 8.2 Markdown and images

- Artefact content is stored as markdown.
- Client-side rendering should support:
  - Headings, lists, code blocks, blockquotes.
  - Inline images with URLs.

### 8.3 Image management and generation

The system must support basic image management and AI image generation in v1.

Users can insert or manage images in the artefact via:

1. **Upload from disk**
   - Select an image file (e.g. `.png`, `.jpg`, `.webp`).
   - The image is stored as a project asset; the artefact stores a markdown image tag pointing to the local asset URL.

2. **Paste from clipboard**
   - Paste an image directly into the artefact editor.
   - The client captures the pasted image, uploads it to the server, and inserts a corresponding markdown image tag.

3. **Image URL**
   - Enter a remote image URL.
   - The artefact stores the URL in a markdown image tag. Optionally, the server may cache a local copy.

4. **Placeholder images**
   - Provide simple controls to insert a placeholder image given width and height (and optionally a keyword or category).
   - The placeholder is retrieved from a configurable placeholder image service (for example, a service that returns random or themed images for a given size).
   - The artefact stores the resulting URL in a markdown image tag.

5. **AI-generated images (Gemini "Nano Banana")**
   - Provide an "Insert AI image" flow that uses a Gemini image generation model (internally referred to as the "Nano Banana" model; the concrete model ID is configurable in the configuration module).
   - The flow should:
     - Offer a text area where the user can either:
       - Provide a precise prompt to send directly to the image model, or
       - Describe in plain language what they want, allowing an intermediate prompt-shaping step.
     - Generate **four** candidate images in a single run and display them as labelled options (Option 1–4).
     - Allow the user to:
       - Select a single option (e.g. "I like option 1"), in which case that image is stored as a project asset and inserted into the artefact, or
       - Provide combinatorial feedback (e.g. "I like the hat in option 1 but the boots in option 4"). In this case, an image-generation agent composes a new prompt merging the referenced features and triggers a follow-up generation round (again producing up to four new options).
   - The system should interpret feedback that references a single option as a selection, and feedback that mentions features from multiple options as a request for a new blended generation.

All generated or uploaded images are stored in a project-scoped asset directory, and artefact markdown references them via stable URLs or relative paths.


## 9. Agent design

### 9.1 General behaviour

Each agent is a higher-level orchestration routine that:

1. Builds a context plan from active resources and current artefact.
2. Calls the LLM one or more times in a loop.
3. Evaluates whether another pass is needed based on a simple reflection heuristic.
4. Produces a new artefact version and logs all intermediate steps.

Agents must be transparent:

- Logs of prompts, responses and context summaries are saved.
- The UI can show a collapsible panel per agent run with these logs.

### 9.2 Writer agent (first draft)

Purpose: convert the user’s audio notes, plus selected source material, into a coherent first draft of a blog post.

Workflow (pseudo):

1. Pass 1:
   - System prompt emphasising: “The user’s audio notes reflect the intended structure and content. Preserve their voice and intentions as much as possible. Use source materials only for clarification and detail.”
   - Include:
     - User’s audio notes (prioritised).
     - Selected source transcripts.
     - Short style summary derived from the blog corpus (if within budget).
   - Ask the model to produce a structured draft in markdown.

2. Pass 2:
   - Ask model to compare the draft against the notes and list items in the notes that are missing or underdeveloped.
   - If missing items are found, instruct model to update the draft to incorporate them.

3. Pass 3 (optional):
   - Ask model to compare with the source materials for obvious factual gaps or misinterpretations.
   - Update draft where appropriate.

4. Save the final version as a new `ArtefactVersion` and record an `AgentRun` with `iteration_count`.

### 9.3 Style Editor agent

Purpose: adjust the draft to better match the user’s established writing style, while avoiding generic “AI voice”.

Workflow:

1. Pre-pass (optional, done once per project):
   - Ask the model, using the blog corpus, to produce a compact style profile (few hundred tokens) describing tone, sentence length, typical structure, quirks, and things to avoid.
   - Store this profile in the project.

2. Style pass:
   - Provide the style profile plus the current artefact.
   - Instruct the model to rewrite only where necessary to move closer to the style profile.
   - Emphasise: do not remove specific details, personal anecdotes, or idiosyncratic phrasing without good reason.

3. Reflection pass:
   - Ask the model to self-assess: list the main style changes it made, and check whether any important content was lost.
   - If content was lost, instruct a correction pass.

4. Save the result as a new version with `created_by_agent = style_editor`.

### 9.4 Detail Editor agent

Purpose: ensure the post is sufficiently detailed and concrete relative to the source material and previous blog posts.

Workflow:

1. Compare current artefact to:
   - Notes.
   - Source material.
   - Optionally, a sampled subset of previous posts that are considered “good” benchmarks.

2. Ask model to:
   - Identify areas that are vague or hand-wavy.
   - Suggest where additional examples, clarifications or code snippets are needed.

3. Apply these changes to the artefact.

4. Save as a new version.

### 9.5 Fact Checker agent

Purpose: check the draft for factual accuracy against the provided source materials.

Workflow:

1. For each factual claim in the artefact (heuristic: sentences containing numbers, named entities, or technical terms):
   - Ask model to cross-reference with the active source materials only.

2. Annotate the artefact with:
   - Confirmed facts.
   - Flags where the source does not support the claim or appears to contradict it.

3. Optionally, create a “fact check report” in a separate section.

4. Save an annotated version as a new artefact version.


## 10. Agent monitoring UI

### 10.1 Requirements

- Each time an agent runs, the UI shows an entry in an “Agent runs” list.
- Clicking an entry expands a panel that shows:
  - Agent type and parameters.
  - Context plan summary (which resources were included, any summarisation).
  - Per-iteration logs:
    - System prompt excerpt.
    - User prompt (if any).
    - Model replies.
    - Token usage (if returned by the API).

- The list should support filtering by project, agent type and status.


## 11. Developer workflow and rules

### 11.1 LLM_docs compliance

- Add a clear guideline in the README and in a `dev_notes.md` file:
  - “Any automated code-writing agent or script used to modify this repository must first read all documents in `LLM_docs/` and must not generate or change code without doing so.”
- Provide a simple Python helper function `load_llm_docs()` that:
  - Reads all files in `LLM_docs/`.
  - Returns their concatenated contents.
  - Can be used in any dev tooling.

### 11.2 Configuration

- Use environment variables for:
  - Gemini API key.
  - Default model.
  - Storage paths.

- Provide a single configuration module that centralises:
  - Model definitions (ID, display name, context size).
  - File size limits.
  - Chunking parameters.

### 11.3 Testing

- Provide unit tests for:
  - Tokenisation and context planning.
  - Resource ingestion for each supported format.
  - Basic agent orchestration (mocking external LLM calls).


## 12. Future extensions (non-blocking for v1)

- Advanced diffing between artefact versions.
- Inline comments and suggestions within the artefact, linked to agent runs.
- Per-paragraph provenance tracking (which sources influenced which parts of the text).
- Collaboration features (multiple authors on one project).
- Model-agnostic plugin system for adding non-Gemini models.


## 13. Definition of done for v1

The tool is considered implemented for v1 when:

1. A user can create a project, upload at least:
   - One set of audio notes as text.
   - One source transcript (e.g. YouTube transcript).
   - One blog corpus document.

2. The token-based context treemap shows the three resources; user can toggle them on and off.

3. The user can:
   - Use the Writer agent to generate a first draft artefact.
   - Use the Style Editor to adjust the draft.
   - View and switch between artefact versions.

4. Agent logs are visible for at least the last run of each agent.

5. Model selection works, and context limits update accordingly in the UI.

6. All code is Python, built on FastHTML with Munster UI components.

7. Basic automated tests pass for the critical flows outlined in this spec.

