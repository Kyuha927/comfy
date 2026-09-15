from __future__ import annotations

from fastapi.testclient import TestClient

from yue2_music_os.api import create_app


def test_note_ir_import_edit_revision_and_exports(settings) -> None:
    with TestClient(create_app(settings)) as client:
        project = client.post("/api/projects", json={"name": "Note API"}).json()
        uploaded = client.post(
            f"/api/projects/{project['id']}/uploads",
            files={"file": ("source.wav", b"RIFF-fake", "audio/wav")},
        )
        assert uploaded.status_code == 201
        imported = client.post(
            "/api/note-ir/import",
            json={
                "project_id": project["id"],
                "source_artifact_id": uploaded.json()["id"],
                "title": "Imported notes",
                "provider_id": "external-free",
                "tracks": [
                    {
                        "instrument": "guitar",
                        "polyphonic": True,
                        "notes": [
                            {
                                "pitch_midi": 68,
                                "start_sec": 1.0,
                                "end_sec": 1.4,
                                "velocity": 90,
                                "confidence": 0.93,
                            }
                        ],
                    }
                ],
            },
        )
        assert imported.status_code == 201
        ir = imported.json()
        note = ir["tracks"][0]["notes"][0]
        assert note["pitch"]["name"] == "G#4"
        edited = client.patch(
            f"/api/note-ir/{ir['music_ir_id']}/notes/{note['note_id']}",
            json={"pitch_midi": 69, "edit_reason": "API correction"},
        )
        assert edited.status_code == 200
        body = edited.json()
        assert body["music_ir"]["revision"] == 2
        assert body["receipt"]["after"]["pitch"]["name"] == "A4"
        assert body["receipt"]["audio_changed"] is False
        revisions = client.get(
            f"/api/note-ir/{ir['music_ir_id']}/revisions"
        ).json()
        assert [item["revision"] for item in revisions] == [2, 1]
        midi = client.get(f"/api/note-ir/{ir['music_ir_id']}/export.mid")
        assert midi.status_code == 200
        assert midi.content.startswith(b"MThd")
        exported_json = client.get(
            f"/api/note-ir/{ir['music_ir_id']}/export.json"
        )
        assert exported_json.status_code == 200
        assert exported_json.json()["revision"] == 2
        assert client.get("/note-editor.html").status_code == 200


def test_note_api_inherits_token_protection(settings) -> None:
    protected = settings.__class__(
        **{
            **{
                field: getattr(settings, field)
                for field in settings.__dataclass_fields__
            },
            "api_token": "secret",
        }
    )
    with TestClient(create_app(protected)) as client:
        assert client.get("/api/note-providers").status_code == 401
        response = client.get(
            "/api/note-providers", headers={"X-Music-OS-Token": "secret"}
        )
        assert response.status_code == 200
        assert any(item["provider_id"] == "normalized-json" for item in response.json())
