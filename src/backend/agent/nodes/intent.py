import json
from langchain_core.messages import HumanMessage
from ..state import AgentState
from ..llm import get_llm_client, get_model_name
from ..cancel import cancel_manager
import logging

logger = logging.getLogger(__name__)


async def intent_classifier_node(state: AgentState) -> dict:
    if cancel_manager.is_cancelled(state["session_id"]):
        return {"cancelled": True}

    last_msg = state["messages"][-1].content if state["messages"] else ""

    client = get_llm_client()
    model = get_model_name()

    system_prompt = (
        "你是意图分类器。分析用户消息，返回JSON格式的意图分类结果。\n"
        "意图类别：\n"
        "- knowledge: 询问知识库相关内容（公司政策、文档、专业知识等需要检索的问题）\n"
        "- chitchat: 日常聊天、问候、闲聊、简单常识\n"
        "- tool_use: 需要调用外部工具（搜索、文件操作、计算等）\n\n"
        '仅返回JSON: {"intent": "...", "reason": "..."}'
    )

    try:
        resp = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": last_msg},
            ],
            temperature=0.1,
            max_tokens=100,
        )
        result_text = resp.choices[0].message.content.strip()
        # Parse JSON
        if "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result = json.loads(result_text)
        intent = result.get("intent", "chitchat")
        reason = result.get("reason", "")
        logger.info(f"Intent: {intent} | Reason: {reason}")

        return {
            "intent": intent,
            "needs_rag": intent == "knowledge",
        }
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}, defaulting to chitchat")
        return {"intent": "chitchat", "needs_rag": False}
