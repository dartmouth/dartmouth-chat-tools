"""
title: Code Execution
version: 0.9.2
"""

import json
import logging
from typing import Optional

from fastapi import Request
from open_webui.utils.sanitize import sanitize_code


log = logging.getLogger(__name__)


class Tools:
    async def execute_code(
        self,
        code: str,
        __request__: Request = None,
        __user__: dict = None,
        __event_emitter__: callable = None,
        __event_call__: callable = None,
        __chat_id__: str = None,
        __message_id__: str = None,
        __metadata__: dict = None,
    ) -> str:
        """
        Execute Python code in a sandboxed environment and return the output.
        Use this to perform calculations, data analysis, generate visualizations,
        or run any Python code that would help answer the user's question.

        :param code: The Python code to execute
        :return: JSON with stdout, stderr, and result from execution
        """
        from uuid import uuid4

        if __request__ is None:
            return json.dumps({'error': 'Request context not available'})

        try:
            # Sanitize code (strips ANSI codes and markdown fences)
            code = sanitize_code(code)

            # Import blocked modules from config (same as middleware)
            from open_webui.config import CODE_INTERPRETER_BLOCKED_MODULES

            # Add import blocking code if there are blocked modules
            if CODE_INTERPRETER_BLOCKED_MODULES:
                import textwrap

                blocking_code = textwrap.dedent(
                    f"""
                    import builtins

                    BLOCKED_MODULES = {CODE_INTERPRETER_BLOCKED_MODULES}

                    _real_import = builtins.__import__
                    def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
                        if name.split('.')[0] in BLOCKED_MODULES:
                            importer_name = globals.get('__name__') if globals else None
                            if importer_name == '__main__':
                                raise ImportError(
                                    f"Direct import of module {{name}} is restricted."
                                )
                        return _real_import(name, globals, locals, fromlist, level)

                    builtins.__import__ = restricted_import
                    """
                )
                code = blocking_code + '\n' + code

            engine = getattr(__request__.app.state.config, 'CODE_INTERPRETER_ENGINE', 'pyodide')
            if engine == 'pyodide':
                # Execute via frontend pyodide using bidirectional event call
                if __event_call__ is None:
                    return json.dumps(
                        {'error': 'Event call not available. WebSocket connection required for pyodide execution.'}
                    )

                output = await __event_call__(
                    {
                        'type': 'execute:python',
                        'data': {
                            'id': str(uuid4()),
                            'code': code,
                            'session_id': (__metadata__.get('session_id') if __metadata__ else None),
                            'files': (__metadata__.get('files', []) if __metadata__ else []),
                        },
                    }
                )

                # Parse the output - pyodide returns dict with stdout, stderr, result
                if isinstance(output, dict):
                    stdout = output.get('stdout', '')
                    stderr = output.get('stderr', '')
                    result = output.get('result', '')
                else:
                    stdout = ''
                    stderr = ''
                    result = str(output) if output else ''

            elif engine == 'jupyter':
                from open_webui.utils.code_interpreter import execute_code_jupyter

                output = await execute_code_jupyter(
                    __request__.app.state.config.CODE_INTERPRETER_JUPYTER_URL,
                    code,
                    (
                        __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_TOKEN
                        if __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH == 'token'
                        else None
                    ),
                    (
                        __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH_PASSWORD
                        if __request__.app.state.config.CODE_INTERPRETER_JUPYTER_AUTH == 'password'
                        else None
                    ),
                    __request__.app.state.config.CODE_INTERPRETER_JUPYTER_TIMEOUT,
                )

                stdout = output.get('stdout', '')
                stderr = output.get('stderr', '')
                result = output.get('result', '')

            else:
                return json.dumps({'error': f'Unknown code interpreter engine: {engine}'})

            # Handle image outputs (base64 encoded) - replace with uploaded URLs
            # Get actual user object for image upload (upload_image requires user.id attribute)
            if __user__ and __user__.get('id'):
                from open_webui.models.users import Users
                from open_webui.utils.files import get_image_url_from_base64

                user = await Users.get_user_by_id(__user__['id'])

                # Extract and upload images from stdout
                if stdout and isinstance(stdout, str):
                    stdout_lines = stdout.split('\n')
                    for idx, line in enumerate(stdout_lines):
                        if 'data:image/png;base64' in line:
                            image_url = await get_image_url_from_base64(
                                __request__,
                                line,
                                __metadata__ or {},
                                user,
                            )
                            if image_url:
                                stdout_lines[idx] = f'![Output Image]({image_url})'
                    stdout = '\n'.join(stdout_lines)

                # Extract and upload images from result
                if result and isinstance(result, str):
                    result_lines = result.split('\n')
                    for idx, line in enumerate(result_lines):
                        if 'data:image/png;base64' in line:
                            image_url = await get_image_url_from_base64(
                                __request__,
                                line,
                                __metadata__ or {},
                                user,
                            )
                            if image_url:
                                result_lines[idx] = f'![Output Image]({image_url})'
                    result = '\n'.join(result_lines)

            response = {
                'status': 'success',
                'stdout': stdout,
                'stderr': stderr,
                'result': result,
            }

            return json.dumps(response, ensure_ascii=False)
        except Exception as e:
            log.exception(f'execute_code error: {e}')
            return json.dumps({'error': str(e)})
