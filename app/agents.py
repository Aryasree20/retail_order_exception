"""AutoGen adapter. Offline mode uses transparent deterministic specialist checks.
Set AUTOGEN_ENABLED=true and OPENAI_API_KEY to run a real AgentChat team.
"""
import os

def offline_review(report):
    # Each specialist is deliberately read-only; agents cannot mutate orders, money or stock.
    r=report.model_dump(mode='json')
    transcript=[
      {'agent':'PolicyReviewer','finding':f"Policy clauses cited: {', '.join(r['policy_clause']) or 'none'}; recommendation must remain human-approved."},
      {'agent':'OrderInvestigator','finding':f"Recorded order status: {r['verified_order_status']}; evidence count: {len(r['evidence'])}."},
      {'agent':'InventoryChecker','finding':f"Replacement stock available: {r['replacement_stock_available']}; inventory is read-only."},
      {'agent':'CaseManager','finding':f"Synthesized recommendation: {r['recommendation']}; approval_status=REVIEW_REQUIRED."}
    ]
    return {'mode':'offline_deterministic_specialist_review','transcript':transcript,'report':r}

async def autogen_review(report):
    if os.getenv('AUTOGEN_ENABLED','false').lower()!='true': return offline_review(report)
    try:
        from autogen_agentchat.agents import AssistantAgent
        from autogen_agentchat.teams import RoundRobinGroupChat
        from autogen_agentchat.conditions import MaxMessageTermination
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        client=OpenAIChatCompletionClient(model=os.getenv('AUTOGEN_MODEL','gpt-4o-mini'),api_key=os.environ['OPENAI_API_KEY'])
        prompt=f"Review this read-only case report. Do not invent facts or perform actions. Return a concise policy/order/inventory review. Report JSON: {report.model_dump_json()}"
        agents=[AssistantAgent(name=n,model_client=client,system_message=s) for n,s in [
          ('PolicyReviewer','Check cited policy clauses only. Never override source data.'),
          ('OrderInvestigator','Check order evidence and conflicts. Never claim payment changes.'),
          ('InventoryChecker','Check stock evidence only. Never mutate inventory.'),
          ('CaseManager','Synthesize a recommendation for human approval only.')]]
        team=RoundRobinGroupChat(agents,termination_condition=MaxMessageTermination(4))
        result=await team.run(task=prompt)
        await client.close()
        return {'mode':'autogen_agentchat','transcript':[{'agent':getattr(m,'source','agent'),'finding':str(getattr(m,'content',''))} for m in result.messages],'report':report.model_dump(mode='json')}
    except Exception as exc:
        return {'mode':'offline_fallback_after_autogen_error','fallback_reason':str(exc),'transcript':offline_review(report)['transcript'],'report':report.model_dump(mode='json')}
