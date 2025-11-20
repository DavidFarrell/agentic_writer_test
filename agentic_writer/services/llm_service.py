from google import genai
from agentic_writer.config import GEMINI_API_KEY
import os

class LLMService:
    def __init__(self):
        if GEMINI_API_KEY:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        else:
            self.client = None
            print("Warning: GEMINI_API_KEY not set")

    def count_tokens(self, text: str, model_id: str) -> int:
        if not self.client:
            return len(text.split())
        try:
            # Use the count_tokens API
            response = self.client.models.count_tokens(
                model=model_id,
                contents=text
            )
            return response.total_tokens
        except Exception as e:
            print(f"Error counting tokens: {e}")
            return len(text.split()) # Fallback

    def plan_context(self, resources: list, model_id: str, max_tokens: int) -> list:
        """
        Selects resources to include in the context based on token limits.
        Simple strategy: Include all active resources until limit is reached.
        """
        included_resources = []
        current_tokens = 0
        
        # Sort resources by priority (Notes > Source > Corpus > Other)
        # For now, just sort by type string to have deterministic order
        # In real app, add explicit priority field
        sorted_resources = sorted(resources, key=lambda r: r['type'])
        
        for res in sorted_resources:
            if not res['active']:
                continue
                
            if current_tokens + res['token_count'] < max_tokens:
                included_resources.append(res)
                current_tokens += res['token_count']
            else:
                # TODO: Implement summarization or chunking here
                print(f"Skipping resource {res['label']} due to token limit.")
        
        return included_resources

    def run_agent(self, agent_type: str, prompt: str, resources: list, current_artefact: str, model_id: str) -> dict:
        """
        Runs an agent to generate or modify the artefact.
        Returns: {'content': str, 'logs': list}
        """
        if not self.client:
            return {'content': "Error: API Key not set.", 'logs': []}

        # 1. Plan Context
        max_tokens = 1000000 # Placeholder, should fetch from config/model
        context_resources = self.plan_context(resources, model_id, max_tokens)
        
        # 2. Construct Prompt
        context_text = "\n\n".join([f"--- Resource: {r['label']} ({r['type']}) ---\n{r['content']}" for r in context_resources])
        
        system_instruction = ""
        if agent_type == "writer":
            system_instruction = "You are an expert blog post writer. Use the provided notes and sources to write a high-quality blog post."
        elif agent_type == "style_editor":
            system_instruction = "You are a style editor. Refine the text to match the desired style without losing information."
        elif agent_type == "detail_editor":
            system_instruction = "You are a detail editor. Add concrete details and examples where the text is vague."
        elif agent_type == "fact_checker":
            system_instruction = "You are a fact checker. Verify claims against the source material and annotate the text."
        
        full_prompt = f"""
Context Resources:
{context_text}

Current Artefact:
{current_artefact}

User Instruction:
{prompt}

Task:
Perform the {agent_type} task. Return the full markdown of the new artefact version.
"""
        
        # 3. Call LLM
        try:
            response = self.client.models.generate_content(
                model=model_id,
                contents=full_prompt,
                config={'system_instruction': system_instruction}
            )
            
            return {
                'content': response.text,
                'logs': [
                    {'role': 'system', 'content': system_instruction},
                    {'role': 'user', 'content': full_prompt},
                    {'role': 'assistant', 'content': response.text}
                ]
            }
        except Exception as e:
            return {'content': f"Error running agent: {e}", 'logs': []}
