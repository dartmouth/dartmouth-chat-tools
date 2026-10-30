import json

import pytest


from .conftest import cloud_model, local_model, user


async def test_harmless_content_passes_silently(run, classifier, event_call, emitter):
    body = await run([user("Write a haiku about autumn leaves on the Dartmouth Green.")])

    assert body["messages"][0]["content"].startswith("Write a haiku")
    assert classifier.states == [
        "Write a haiku about autumn leaves on the Dartmouth Green."
    ]
    assert event_call.dialogs == []
    assert emitter.events == []


SSN = "Name: Jordan Avery, SSN: 078-05-1120."
FERPA = "Student Liam Chen (ID 12345678) received a D in MATH 13 and is on academic probation."


async def test_disc3_on_cloud_model_prompts(run, classifier, event_call):
    classifier.flag("078-05-1120", flags={"government_id": 0.987}, disc_level=2.93)

    await run([user(SSN)], model=cloud_model())

    assert len(event_call.dialogs) == 1
    message = event_call.dialogs[0]["data"]["message"]
    assert event_call.dialogs[0]["type"] == "confirmation"
    assert "Government ID" in message
    assert "local model" in message


async def test_disc3_on_local_model_passes_silently(run, classifier, event_call):
    classifier.flag("078-05-1120", flags={"government_id": 0.987}, disc_level=2.93)

    await run([user(SSN)], model=local_model())

    assert event_call.dialogs == []


async def test_regulated_data_on_local_model_prompts(run, classifier, event_call):
    classifier.flag("MATH 13", flags={"ferpa": 0.986}, disc_level=2.75)

    await run([user(FERPA)], model=local_model())

    assert len(event_call.dialogs) == 1
    message = event_call.dialogs[0]["data"]["message"]
    assert "FERPA student record" in message
    assert "Information Security" in message


async def test_regulated_data_on_cloud_model_prompts(run, classifier, event_call):
    classifier.flag("MATH 13", flags={"ferpa": 0.986}, disc_level=2.75)

    await run([user(FERPA)], model=cloud_model())

    message = event_call.dialogs[0]["data"]["message"]
    assert "FERPA student record" in message
    assert "Information Security" in message
    assert "not allowed on cloud models" in message


async def test_unclassified_disc3_on_cloud_model_prompts(run, classifier, event_call):
    classifier.flag("donor list", disc_level=2.8)

    await run([user("Here is the confidential donor list.")])

    assert "Other highly confidential data" in event_call.dialogs[0]["data"]["message"]


async def test_directory_information_passes_silently(run, classifier, event_call):
    classifier.flag("f00abc1", flags={"personal_details": 0.02}, disc_level=0.94)

    await run([user("Email Taylor Brooks (taylor.r.brooks@dartmouth.edu, NetID f00abc1).")])

    assert event_call.dialogs == []


async def test_confirming_sends_the_request_unchanged(run, classifier, event_call):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})
    event_call.result = True

    body = await run([user(SSN)])

    assert body["messages"] == [user(SSN)]


@pytest.mark.parametrize(
    "result",
    [
        False,
        {"error": "Client session disconnected."},
        {"error": "Event call timed out. The browser tab may be inactive or closed."},
        None,
        "true",
    ],
)
async def test_anything_but_true_cancels_the_request(run, classifier, event_call, result):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})
    event_call.result = result

    with pytest.raises(Exception) as cancelled:
        await run([user(SSN)])

    assert "Nothing was sent" in str(cancelled.value)
    assert "switch off the DISC Risk Gate" in str(cancelled.value)


async def test_cancel_message_gives_advice_for_what_was_found(run, classifier, event_call):
    classifier.flag("MATH 13", flags={"ferpa": 0.986})
    event_call.result = False

    with pytest.raises(Exception) as cancelled:
        await run([user(FERPA)])

    assert "Information Security" in str(cancelled.value)


async def test_without_a_session_the_request_passes_unchecked(run, classifier):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})

    body = await run([user(SSN)], __event_call__=None)

    assert body["messages"] == [user(SSN)]
    assert classifier.requests == []


def tool_turn(tool: str, arguments: dict, result: str, call_id: str = "call_1") -> list[dict]:
    """An assistant tool call followed by its result, as sent to the provider."""
    return [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": call_id,
                    "type": "function",
                    "function": {"name": tool, "arguments": json.dumps(arguments)},
                }
            ],
        },
        {"role": "tool", "tool_call_id": call_id, "content": result},
    ]


def dialog_text(event_call) -> str:
    return event_call.dialogs[0]["data"]["message"]


async def test_finding_in_a_tool_result_names_the_tool(run, classifier, event_call):
    classifier.flag("MATH 13", flags={"ferpa": 0.987})

    await run(
        [
            user("Who is on probation?"),
            *tool_turn("query_knowledge_files", {"query": "probation"}, FERPA),
        ]
    )

    assert "query_knowledge_files" in dialog_text(event_call)
    assert FERPA in classifier.states


async def test_finding_in_attachment_content_names_the_file(run, classifier, event_call):
    classifier.flag("MATH 13", flags={"ferpa": 0.987})
    result = json.dumps(
        {"handle": "att_0", "type": "file", "id": "f1", "filename": "roster.csv", "content": FERPA}
    )

    await run(
        [
            user("Summarise the attached file."),
            *tool_turn("view_attachment", {"handle": "att_0"}, result),
        ]
    )

    assert "attached file roster.csv" in dialog_text(event_call)


async def test_finding_in_retrieved_context_says_so(run, classifier, event_call):
    classifier.flag("MATH 13", flags={"ferpa": 0.987})
    system = (
        "### Task:\nRespond to the user query using the provided context.\n"
        f'<context>\n<source id="1" name="advising.pdf">{FERPA}</source>\n</context>'
    )

    await run([{"role": "system", "content": system}, user("Who is on probation?")])

    assert "retrieved context" in dialog_text(event_call)


async def test_multipart_user_content_is_checked(run, classifier, event_call):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})

    await run(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SSN},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
                ],
            }
        ]
    )

    assert "your message" in dialog_text(event_call)
    assert classifier.states == [SSN]


async def test_all_findings_appear_in_one_dialog(run, classifier, event_call):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})
    classifier.flag("MATH 13", flags={"ferpa": 0.987})

    await run(
        [
            user(SSN),
            *tool_turn("query_knowledge_files", {"query": "probation"}, FERPA),
        ]
    )

    assert len(event_call.dialogs) == 1
    message = dialog_text(event_call)
    assert "Government ID" in message
    assert "FERPA student record" in message
    assert message.index("Regulated data") < message.index("cloud model")


async def test_dialog_never_shows_the_sensitive_value(run, classifier, event_call):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})
    event_call.result = False

    with pytest.raises(Exception) as cancelled:
        await run([user(SSN)])

    assert "078-05-1120" not in json.dumps(event_call.dialogs)
    assert "Jordan Avery" not in json.dumps(event_call.dialogs)
    assert "078-05-1120" not in str(cancelled.value)


@pytest.fixture
def ssn_flagged(classifier):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})


def workspace_model(base_model_id: str, tags: list | None = None) -> dict:
    return {
        "id": "my-assistant",
        "info": {"base_model_id": base_model_id, "meta": {"tags": tags or []}},
    }


async def test_untagged_model_counts_as_cloud(run, ssn_flagged, event_call):
    await run([user(SSN)], model={"id": "mystery", "info": {"meta": {}}})

    assert len(event_call.dialogs) == 1


async def test_local_tag_in_model_meta_counts_as_local(run, ssn_flagged, event_call):
    model = {"id": "dartmouth.llama", "info": {"meta": {"tags": [{"name": "local"}]}}}

    await run([user(SSN)], model=model)

    assert event_call.dialogs == []


async def test_workspace_model_on_a_local_base_counts_as_local(run, ssn_flagged, event_call):
    base = local_model("dartmouth.llama")

    await run([user(SSN)], model=workspace_model(base["id"]), registry=[base])

    assert event_call.dialogs == []


async def test_workspace_model_on_a_cloud_base_counts_as_cloud(run, ssn_flagged, event_call):
    base = cloud_model("openai.gpt-5")

    await run(
        [user(SSN)],
        model=workspace_model(base["id"], tags=[{"name": "local"}]),
        registry=[base],
    )

    assert len(event_call.dialogs) == 1


async def test_workspace_model_with_unknown_base_counts_as_cloud(run, ssn_flagged, event_call):
    await run([user(SSN)], model=workspace_model("gone.model"))

    assert len(event_call.dialogs) == 1


def couldnt_check(emitter) -> bool:
    return any("couldn't check" in d for d in emitter.descriptions)


@pytest.mark.parametrize("status", [400, 401, 500])
async def test_classifier_error_fails_open_with_a_notice(
    run, classifier, event_call, emitter, status
):
    classifier.status = status

    body = await run([user(SSN)])

    assert body["messages"] == [user(SSN)]
    assert event_call.dialogs == []
    assert couldnt_check(emitter)


async def test_unusable_classifier_response_fails_open(run, classifier, emitter):
    classifier.raw_body = b"<html>Bad gateway</html>"

    await run([user(SSN)])

    assert couldnt_check(emitter)


async def test_classifier_timeout_fails_open(run, gate, classifier, emitter):
    gate.valves.classifier_timeout = 0.05
    classifier.delay = 1

    await run([user(SSN)])

    assert couldnt_check(emitter)


async def test_unconfigured_proxy_fails_open(run, classifier, emitter, monkeypatch):
    monkeypatch.delenv("LITELLM_PROXY_BASE_URL")

    await run([user(SSN)])

    assert couldnt_check(emitter)
    assert classifier.requests == []


async def test_a_repeated_finding_prompts_on_every_provider_call(run, ssn_flagged, event_call):
    await run([user(SSN)])
    await run([user(SSN), *tool_turn("get_current_timestamp", {}, "2026-10-29")])

    assert len(event_call.dialogs) == 2


async def test_message_too_long_to_check_blocks_the_request(run, gate, classifier, event_call):
    classifier.flag("big table", input_tokens=16384)

    with pytest.raises(Exception) as blocked:
        await run([user("Hello"), user("big table ...")])

    assert "too long to be checked" in str(blocked.value)
    assert "switch off the DISC Risk Gate" in str(blocked.value)
    assert event_call.dialogs == []


async def test_obviously_too_long_message_is_not_sent_to_the_classifier(
    run, gate, classifier
):
    gate.valves.classifier_max_input_tokens = 100

    with pytest.raises(Exception, match="too long to be checked"):
        await run([user("x" * 801)])

    assert classifier.requests == []


async def test_too_long_message_without_a_session_passes(run, classifier):
    classifier.flag("big table", input_tokens=16384)

    body = await run([user("big table ...")], __event_call__=None)

    assert body["messages"] == [user("big table ...")]


async def test_logs_never_contain_message_content(run, classifier, event_call, caplog):
    caplog.set_level("DEBUG")
    classifier.flag("078-05-1120", flags={"government_id": 0.987})
    event_call.result = False
    with pytest.raises(Exception):
        await run([user(SSN)])

    classifier.status = 400  # LiteLLM's 400 bodies echo the request content
    await run([user(f"Check this: {SSN}")])

    assert "078-05-1120" not in caplog.text
    assert "Jordan Avery" not in caplog.text


async def test_each_pass_through_the_tool_loop_only_classifies_new_messages(
    run, classifier
):
    first = [user("What time is it?")]
    await run(first)
    await run([*first, *tool_turn("get_current_timestamp", {}, "2026-10-29T10:00")])

    assert classifier.states == ["What time is it?", "2026-10-29T10:00"]


async def test_obviously_too_long_message_blocks_even_if_the_classifier_is_slow(
    run, gate, classifier
):
    gate.valves.classifier_max_input_tokens = 100
    gate.valves.classifier_timeout = 0.05
    classifier.delay = 1

    with pytest.raises(Exception, match="too long to be checked"):
        await run([user("Hello"), user("x" * 801)])


async def test_obviously_too_long_message_blocks_even_if_the_proxy_is_unconfigured(
    run, gate, monkeypatch
):
    monkeypatch.delenv("LITELLM_PROXY_BASE_URL")
    gate.valves.classifier_max_input_tokens = 100

    with pytest.raises(Exception, match="too long to be checked"):
        await run([user("x" * 801)])


async def test_attached_text_items_are_named(run, classifier, event_call):
    classifier.flag("MATH 13", flags={"ferpa": 0.987})
    result = json.dumps({"handle": "att_1", "type": "text", "name": "advising notes", "content": FERPA})

    await run([user("Summarise it."), *tool_turn("view_attachment", {"handle": "att_1"}, result)])

    assert "attached file advising notes" in dialog_text(event_call)


async def test_retrieved_context_in_a_user_message_points_at_both(run, classifier, event_call):
    classifier.flag("078-05-1120", flags={"government_id": 0.987})
    content = f'<context><source id="1">Policy text</source></context>\n{SSN}'

    await run([user(content)])

    assert "your message or the retrieved context" in dialog_text(event_call)


async def test_local_tag_matches_regardless_of_case(run, ssn_flagged, event_call):
    model = {"id": "dartmouth.llama", "tags": [{"name": "Tool Calling"}, {"name": "Local"}]}

    await run([user(SSN)], model=model)

    assert event_call.dialogs == []
