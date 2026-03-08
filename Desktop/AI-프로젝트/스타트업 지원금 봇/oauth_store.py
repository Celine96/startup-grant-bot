"""
Slack OAuth 저장소 - Google Sheets 기반 InstallationStore + 인메모리 OAuthStateStore
"""

import time
import uuid
import logging

from slack_sdk.oauth.installation_store import InstallationStore, Bot, Installation
from slack_sdk.oauth.state_store import OAuthStateStore

from db import save_installation, get_installation, delete_installation

logger = logging.getLogger(__name__)

STATE_TTL_SECONDS = 600  # 10분


class GoogleSheetsInstallationStore(InstallationStore):
    """Google Sheets에 설치 정보를 저장하는 InstallationStore"""

    def save(self, installation: Installation):
        save_installation(
            team_id=installation.team_id,
            data={
                'team_name': installation.team_name or '',
                'bot_token': installation.bot_token,
                'bot_user_id': installation.bot_user_id or '',
            },
        )

    def find_installation(
        self,
        *,
        enterprise_id=None,
        team_id=None,
        user_id=None,
        is_enterprise_install=None,
    ) -> Installation | None:
        if not team_id:
            return None
        inst = get_installation(team_id)
        if not inst:
            return None
        return Installation(
            team_id=inst['team_id'],
            team_name=inst.get('team_name', ''),
            bot_token=inst['bot_token'],
            bot_user_id=inst.get('bot_user_id', ''),
        )

    def find_bot(
        self,
        *,
        enterprise_id=None,
        team_id=None,
        is_enterprise_install=None,
    ) -> Bot | None:
        installation = self.find_installation(team_id=team_id)
        if not installation:
            return None
        return Bot(
            team_id=installation.team_id,
            bot_token=installation.bot_token,
            bot_user_id=installation.bot_user_id,
        )

    def delete_installation(
        self,
        *,
        enterprise_id=None,
        team_id=None,
        user_id=None,
    ) -> None:
        if team_id:
            delete_installation(team_id)

    def delete_bot(
        self,
        *,
        enterprise_id=None,
        team_id=None,
    ) -> None:
        if team_id:
            delete_installation(team_id)


class InMemoryOAuthStateStore(OAuthStateStore):
    """인메모리 OAuth state 관리 (TTL 10분)"""

    def __init__(self):
        self._states: dict[str, float] = {}

    def issue(self, *args, **kwargs) -> str:
        state = str(uuid.uuid4())
        self._states[state] = time.time()
        self._cleanup()
        return state

    def consume(self, state: str) -> bool:
        self._cleanup()
        issued_at = self._states.pop(state, None)
        if issued_at is None:
            return False
        return (time.time() - issued_at) < STATE_TTL_SECONDS

    def _cleanup(self):
        """만료된 state 정리"""
        now = time.time()
        expired = [s for s, t in self._states.items() if (now - t) >= STATE_TTL_SECONDS]
        for s in expired:
            del self._states[s]
