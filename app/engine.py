import asyncio  #toolkit for doing other work while waiting


class EchoEngine:  #blueprint for the machine
    name = "echo-stub"  #label on the machine

    async def generate(self, prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> dict:
        await asyncio.sleep(0.05)  #pretend the machine takes 0.05 seconds
                                    #if you make it 3 it will become slow 
        return {"text": f"[ECHO] {prompt}"}


ml_models: dict = {}  #the equipment room, empty until the morning routine runs
