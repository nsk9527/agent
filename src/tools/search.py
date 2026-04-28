import os
from serpapi import SerpApiClient


class SearchTool:
    name = "search"
    desc = "一个基于SerpApi的实战网页搜索引擎工具。它会智能地解析搜索结果，优先返回直接答案或知识图谱信息。"
    description = desc

    def __init__(
            self,
            *,
            api_key_env: str = "SERPAPI_API_KEY",
            engine: str = "google",
            gl: str = "cn",
            hl: str = "zh-cn",
    ):
        self.api_key_env = api_key_env
        self.engine = engine
        self.gl = gl
        self.hl = hl

    def __call__(self, query: str) -> str:
        return self.run(query)

    def run(self, query: str) -> str:
        print(f"🔍 正在执行 [SerpApi] 网页搜索: {query}")
        try:
            api_key = os.getenv(self.api_key_env)
            if not api_key:
                return f"[ERROR:INVALID_ARGUMENT] 错误:{self.api_key_env} 未在 .env 文件中配置。"

            params = {
                "engine": self.engine,
                "q": query,
                "api_key": api_key,
                "gl": self.gl,  # 国家代码
                "hl": self.hl,  # 语言代码
            }

            client = SerpApiClient(params)
            results = client.get_dict()

            # 智能解析:优先寻找最直接的答案
            if "answer_box_list" in results:
                return "\n".join(results["answer_box_list"])
            if "answer_box" in results and "answer" in results["answer_box"]:
                return results["answer_box"]["answer"]
            if "knowledge_graph" in results and "description" in results["knowledge_graph"]:
                return results["knowledge_graph"]["description"]
            if "organic_results" in results and results["organic_results"]:
                # 如果没有直接答案，则返回前三个有机结果的摘要
                snippets = [
                    f"[{i + 1}] {res.get('title', '')}\n{res.get('snippet', '')}"
                    for i, res in enumerate(results["organic_results"][:3])
                ]
                return "\n\n".join(snippets)

            return f"[ERROR:EMPTY_RESULT] 对不起，没有找到关于 '{query}' 的信息。"

        except Exception as e:
            return f"[ERROR:EXECUTION] 搜索时发生错误: {e}"
