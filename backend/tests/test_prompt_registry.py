from backend.app.core.prompt_registry import PromptRegistry


def test_prompt_registry_loading_and_rendering(tmp_path):
    # Setup temp prompts directory
    prompt_file = tmp_path / "test_chain.txt"
    prompt_file.write_text("Hello {name}, welcome to {service}!", encoding="utf-8")

    registry = PromptRegistry(prompts_dir=str(tmp_path))
    content = registry.get_prompt("test_chain")
    assert "Hello {name}" in content

    rendered = registry.render("test_chain", name="Alice", service="PromptForge")
    assert rendered == "Hello Alice, welcome to PromptForge!"

    # Test hot reload on file edit
    prompt_file.write_text("Updated greeting for {name} on {service}.", encoding="utf-8")
    registry.reload()
    updated_rendered = registry.render("test_chain", name="Bob", service="Forge")
    assert updated_rendered == "Updated greeting for Bob on Forge."

def test_prompt_registry_default_dir():
    registry = PromptRegistry()
    available = registry.list_available_prompts()
    assert "chain_1_intent_decomposition" in available
    prompt = registry.get_prompt("chain_1_intent_decomposition")
    assert "Intent Decomposition" in prompt
