---
title: "AI Weekly Reads - 2026-07-13"
aliases:
  - "AI Weekly Reads - 2026-07-13"
  - "AI Weekly Reads 2026-07-13"
created: "2026-07-13"
type: "weekly-book"
status: "ready"
language: "en"
---

# AI Weekly Reads

Week of 2026-07-13

[Download the latest EPUB for Kindle](latest.epub)

## Contents

### 📰 General AI & Tech Insights

1. [Tanay Jaipuria / x_thread] Thu Jul 02 - RL Beyond the Verifiable
2. [web / Web] 2026-07-13 - Scaling Laws, Carefully | Lil'Log
3. [Michele Catasta / x_thread] Mon Jul 06 - Continual Learning for Agents
4. [web / Web] 2026-07-13 - Harness Engineering for Self-Improvement | Lil'Log
5. [web_transcript / Web Transcript] 2026-07-13 - Multi-Agent AI Is Already Inside Enterprise Workflows | Venkat Siva (Sivasubramanian)
6. [Shilong Liu / x_thread] Wed Jul 08 - A Taxonomy of Self-evolving Agents
7. [Sergio Paniego / x_thread] Wed Jul 08 - Distillation in 2026 (so far): which frontier models use it and how 
8. [will depue / x_thread] Mon Jul 06 - X Post by will depue
9. [Sean Cai / x_thread] Tue Jul 07 - X Post by Sean Cai
10. [web / Web] 2026-07-13 - https://z.ai/blog/glm-5.2
11. [Resolve AI - AI for Prod / YouTube] 2026-07-13 - The Art of Scaling Reinforcement Learning for LLMs | Sean Bell, Resolve AI Labs
12. [web / Web] 2026-07-13 - victoria_lin_stanford_cs25_transformers_united_2026.pdf - Google Drive
13. [web / Web] 2026-07-13 - Be impatient | benkuhn.net
14. [web / Web] 2026-07-13 - https://cameronrwolfe.substack.com/p/agentic-rl
15. [Sam Z Liu / x_thread] Sat Jul 11 - Hot takes on AI memory

## Reading Notes

### 📰 General AI & Tech Insights

# RL Beyond the Verifiable

> 📅 **Published:** Thu Jul 02  |  🔗 **Source:** [Tanay Jaipuria](https://x.com/tanayj/status/2072766211256119475)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

On a podcast with Dwarkesh, Dario Amodei, CEO of Anthropic, said he’s 90% sure we get a “country of geniuses in a data center” within ten years. And when he explains the missing 10%, his biggest uncertainty comes down to one thing, the tasks you can’t verify: > With coding, except for that irreducible uncertainty, I think we’ll be there in one or two years. There’s no way we will not be there in ten years in terms of being able to do end-to-end coding. My one little bit of fundamental uncertainty, even on long timescales, is about tasks that aren’t verifiable: planning a mission to Mars; doing some fundamental scientific discovery like CRISPR; writing a novel. It’s hard to verify those tasks. That’s what we’ll discuss today. In this piece, I’ll cover: - Why verifiability is the constraint - The techniques that are working now - The companies attacking the problem ## I. The verifiability constraint A big reason for the progress over the last year has been RL with verifiable rewards, or RLVR. The idea is simple. Give the model a problem where you can check or verify the answer, let it reason through to a solution, and reinforce the attempts that land on the right one. Math and code are the perfect fit and we’ve seen the corresponding progress. The reward is clean, cheap, and you can run it millions of times. And the hill-climbing has been real as evidenced by the progress on SWE-bench. In 2025...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# Scaling Laws, Carefully | Lil'Log

> 📅 **Added:** 2026-07-13  |  🔗 **Source:** [web](https://lilianweng.github.io/posts/2026-06-24-scaling-laws/)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

Scaling Laws, Carefully Date: June 24, 2026 | Estimated Reading Time: 25 min | Author: Lilian Weng Table of Contents Early days: ML loss predictability Scaling Laws in Data-Infinite Region Kaplan et al.’s Scaling Laws Chinchilla Scaling Laws Method 1: Fix model sizes, vary the token budget Method 2: IsoFLOP profiles Method 3: Parametric fit Reconciling Kaplan and Chinchilla Why power law? Scaling Laws in Data-Limited Region Trickiness of Fitting Scaling Laws in Reality Toy simulation Citation References Scaling laws are one of the most critical empirical findings in deep learning. The observation is simple in form: the training loss $L$ decreases predictably as we scale up model size $N$, dataset size $D$, and compute $C$, following a power-law curve, which appears as a straight line on a log-log plot. We can view scaling laws as a framework for describing the relationship between compute, loss, model size and data; at its core, it is about how to allocate precious compute optimally between $N$ and $D$. This predictability makes scaling laws highly valuable in practice. A common workflow is to fit scaling laws on a handful of small runs and then extrapolate to estimate the token and compute requirements for larger models. Symbol Note $N$ Model size, measured in parameter count. $D$ Training dataset size, usually measured in token count. $C$ Training compute in FLOPs. As a useful approximation, $C \approx 6ND$ ( Kaplan et al. 2020 ), where $2ND$ accounts for the forward pass and $4ND$ for backpropagation. $E$ Irreducible...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# Continual Learning for Agents

> 📅 **Published:** Mon Jul 06  |  🔗 **Source:** [Michele Catasta](https://x.com/i/status/2074118901143679414)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

Everyone talks about Continual Learning as if it means one thing only: updating model weights. But there's an inconvenient truth about the agent ecosystem — the vast majority of agents in production today leverage closed frontier models. When you don't own the weights, you certainly can't fine-tune them. For most agent builders, weight-level continual learning is off the table, especially when working at the very frontier of capabilities (think Fable 5 or GPT 5.6). That doesn't mean agents can't learn. Agentic systems can improve at three layers — model, harness, and context [0] — and the last two are fully within your control. This is where the a massive (but often overlooked) opportunity lies: harness-level learning lets you mine production traces to systematically improve the code, tools, and instructions that power every instance of your agent, while context-level learning lets you personalize at the agent, user, and org level, so your product gets better with every interaction. Do all the above, and you will be compounding improvements that you can ship daily. In the rest of this article, I'll walk through how we've been applying continual learning to Replit Agent for the past year, and share all the lessons we learned along the way. ## Evaluating and improving Replit Agent at scale Most Replit Agent users start with an idea. They describe the goal in natural language — without a repo, test suite, or chosen framework — and expect the agent to turn it into a functioning app. The result...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# Harness Engineering for Self-Improvement | Lil'Log

> 📅 **Added:** 2026-07-13  |  🔗 **Source:** [web](https://lilianweng.github.io/posts/2026-07-04-harness/)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

Harness Engineering for Self-Improvement Date: July 4, 2026 | Estimated Reading Time: 28 min | Author: Lilian Weng Table of Contents Harness Design Patterns Pattern 1: Workflow Automation Pattern 2: File System as Persistent Memory Pattern 3: Sub-agent and Backend Jobs Case study: Coding Agent Harness Harness Layer vs Core Intelligence? Harness Optimization Context Engineering Workflow Design Self-Improving Harness Evolutionary Search Joint Optimization with Model Weights Future Challenges Citation Appendix: Some useful benchmarks References The concept of recursive self-improvement (RSI) dates back to I. J. Good (1965) , where he defined an “ultraintelligent machine” as a system that can surpass humans in all intellectual activities and design better machines to improve itself. Yudkowsky (2008) used the phrase “recursive self-improvement” for a specific feedback loop: an AI uses its current intelligence to improve the cognitive machinery that produces its intelligence. This feedback loop in modern AI may indicate the model rewriting its own weights directly, or more broadly the model improves the training pipeline and the deployment system , which in turn enables a better successor model with improved performance across economically valuable tasks. The speed of research development in AI has been shown to drastically accelerated in frontier labs ( Anthropic ; OpenAI ). I explicitly mention “deployment system” because the layer between the raw model and the real-world context seems to be as important as the model’s raw intelligence (i.e. the evals right after pretraining). Harnesses are important components of AI deployment, as shown by successful coding agent products...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# Multi-Agent AI Is Already Inside Enterprise Workflows | Venkat Siva (Sivasubramanian)

> 📅 **Added:** 2026-07-13  |  🔗 **Source:** [web_transcript](https://www.linkedin.com/posts/venkiz_ive-been-rethinking-how-we-talk-about-multi-agent-ugcPost-7480266268256927744-Cn9l/?utm_source=social_share_send&utm_medium=android_app&rcm=ACoAADARLHEB_UFphINLzHGX7sK5hyGvTD0nnHQ&utm_campaign=share_via)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

Venkat Siva (Sivasubramanian)’s Post Venkat Siva (Sivasubramanian) 6d Report this post I’ve been rethinking how we talk about multi-agent AI. The useful question is rarely: “how many agents are in the system?” It is: “how much authority did we delegate?” A support assistant drafting a reply based on customer history. A coding agent reviewing a pull request and running tests. A renewal workflow splitting tasks across contract review, usage analysis, and account research. These systems look different, but the enterprise problem is similar. Once an AI system can interpret a goal, access context, choose tools, and produce an action, we need to understand the path from request to outcome. That execution path is where the governance problem begins. I wrote more about why “delegated authority” is becoming a better lens for enterprise AI, and why defining the autonomy envelope is our next infrastructure challenge. Curious how other builders are thinking about this. Multi-Agent AI Is Already Inside Enterprise Workflows Venkat Siva (Sivasubramanian) on LinkedIn 19 7 Comments Like Comment Share Copy LinkedIn Facebook X Moonveil AI 5d Report this comment Delegated authority is the cleanest lens because it forces the boring questions early: what data can the system touch, what actions are reversible, and where does a human re-enter without digging through a transcript. Multi-agent diagrams look impressive, but the autonomy envelope is the real product spec. Are you seeing teams define that envelope at design time, or only after the first near-miss? Like Reply 1 Reaction Aditi Soory 5d...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# A Taxonomy of Self-evolving Agents

> 📅 **Published:** Wed Jul 08  |  🔗 **Source:** [Shilong Liu](https://x.com/i/status/2074800880017342665)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

Self-evolving agents are becoming popular. [Hermes Agent](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills) enables automatic reusable skills. [RSI Lab](https://www.recursive.com/) tries to discover new algorithms recursively. NVIDIA explores [agentic self-evolving for robots](https://research.nvidia.com/labs/gear/enpire/). Auto-research agents aim to self-evolve for scientific discovery. More papers are also designing self-evolving algorithms, including both reinforcement learning (RL) and training-free methods. They all use similar words: self-evolving, self-improving, learning, adapting. But do they mean the same thing? How should we classify these works into different directions? And how are they different from related terms like self-improving agents, recursive self-improvement, continual learning, and test-time training? In this blog, I provide a taxonomy for self-evolving agents by answering these questions. ## Models, Harness, and Artifacts Models, harness, and artifacts are three key factors in a self-evolving system. Models, usually large language models (LLMs), are the brains that respond to prompts. Harness includes loop designs, memory, tools, and other surrounding components. It turns models into agents. Hence there is a famous equation: > Agent = Model + Harness Artifacts are mentioned less often. I use the term "artifact" for the outputs produced by agents, such as kernel algorithms discovered by agents, papers and findings from auto-researchers, or new robot policies from robotic self-evolving systems. The connections among them are simple. Models and harness work together to form agents. Agents then produce artifacts. Together, these three terms give us a useful way to organize self-evolving systems. With this view, existing self-evolving systems can be grouped into three levels: artifact iterative optimization, harness self-improvement, and model learning without...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# Distillation in 2026 (so far): which frontier models use it and how 

> 📅 **Published:** Wed Jul 08  |  🔗 **Source:** [Sergio Paniego](https://x.com/i/status/2074863503312044499)

## One-Sentence Takeaway

Distillation has become a versatile and essential post-training technique for frontier models in 2026, enabling efficient compression, merging of specialized RL experts, and self-improvement for continual learning.

## Short Summary

Distillation, a technique where a smaller "student" model learns from a larger or more specialized "teacher" model, is now a cornerstone of post-training recipes for advanced AI models. It addresses key challenges in model development, such as reducing model size, integrating diverse capabilities, and maintaining performance during iterative training. The article outlines three primary applications: the classic use of a large teacher training a smaller student, the modern approach of merging multiple specialized RL experts into a single unified model, and self-distillation where a model learns from a better version of itself.

This widespread adoption by leading labs like Google, DeepSeek, NVIDIA, and Cursor highlights distillation's practical advantages over traditional reinforcement learning (RL) methods. Distillation provides dense, token-level feedback, allowing for faster convergence and more precise behavior shaping compared to RL's single, sparse reward signal. Its ability to efficiently transfer knowledge, specialize models, and facilitate continual learning makes it a critical component for developing robust, performant, and adaptable AI systems.

## Main Ideas

*   **Off-Policy Distillation for Model Compression:** The traditional use of distillation involves a large, instruction-tuned (IT) teacher model training a smaller student model, often via fine-tuning on the teacher's generated text (hard labels) or matching its next-token distribution (soft labels).
*   **On-Policy Distillation for Merging RL Experts:** A newer, widely adopted method involves training separate RL experts for different domains (e.g., math, code) and then distilling their combined knowledge into a single student model. These "teachers" are typically specialized checkpoints of the same base model, not necessarily larger.
*   **Distillation's Efficiency Over RL:** Labs favor distillation because it provides dense, token-level feedback to the student, allowing for much faster and more precise convergence on desired behaviors compared to the sparse, attempt-level reward signals of reinforcement learning.
*   **Self-Distillation for Behavior Shaping and Continual Learning:** Models can act as their own teachers. This includes injecting hints into the context to guide a model, which then learns to produce the desired behavior without the hint, or distilling from an earlier checkpoint to restore lost capabilities after fine-tuning on new data.
*   **Versatility Across Training Stages:** Distillation is applied not only across different domains but also across sequential RL training phases to recover capabilities that might degrade during subsequent stages.

## Questions And Answers

No distinct Q&A section.

## Notable Details

*   Gemma 3 and Gemma 4's post-training recipes rely on improved knowledge distillation from large instruction-tuned teachers.
*   DeepSeek-R1-Distill used reasoning traces from a large R1 model to train compact Qwen and Llama students via sequence-level fine-tuning (hard labels).
*   DeepSeek-V4's pipeline trains a unified model through on-policy distillation, optimizing reverse KL loss against specialized domain experts (SFT then GRPO).
*   MiMo-V2-Flash introduced Multi-Teacher On-Policy Distillation (MOPD), where multiple domain teachers provide dense, token-level signals.
*   Qwen3's report claims distillation achieved better results at roughly 1/10 the GPU hours compared to RL for similar outcomes.
*   Cursor's Composer 2.5 uses self-distillation by having a hint-conditioned version of the model act as a teacher for its unhinted self, enabling behavior without explicit prompts at inference.

## Actionable Takeaways

*   **Investigate Distillation for Model Efficiency:** Consider distillation as a primary strategy for compressing large models or creating smaller, more efficient versions without significant performance loss.
*   **Adopt Multi-Teacher Distillation for Multi-Domain Models:** For models requiring expertise across diverse domains, explore training specialized RL experts and then merging them into a single model using on-policy distillation.
*   **Leverage Self-Distillation for Continual Learning:** Implement self-distillation techniques to help models retain prior knowledge while learning new skills, addressing the challenge of catastrophic forgetting in continual learning scenarios.
*   **Prioritize Token-Level Feedback:** Recognize that distillation's ability to provide dense, token-level feedback offers a significant advantage in training efficiency and precision over sparse reward signals in traditional RL.

## People, Companies, Tools, And Links Mentioned

*   **People:** Ben, Sasha Rush (@srush_nlp), Dwarkesh Patel, Rafa Nadal
*   **Companies:** Google, DeepSeek, NVIDIA, Thinking Machines, Cursor
*   **Models/Products:** Gemma 3, Gemma 4, DeepSeek-R1-Distill, Qwen, Llama, DeepSeek-V4, MiMo-V2-Flash, GLM-5, Nemotron 3 Ultra, Qwen3, Cursor's Composer 2.5
*   **Tools:** TRL
*   **Links:**
    *   Distillation in 2026 (so far): which frontier models use it and how: [https://x.com/i/status/2074863503312044499](https://x.com/i/status/2074863503312044499)

## Reading Priority

Medium – This article provides a highly concrete and timely overview of how knowledge distillation is being practically applied by leading AI labs in 2026, detailing specific mechanisms and models.

***

# X Post by will depue

> 📅 **Published:** Mon Jul 06  |  🔗 **Source:** [will depue](https://x.com/i/status/2074178395462848800)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

A Stargate for Data Labs are on a trajectory towards >$100B/year of data spend by 2030. As we begin the trillion-dollar compute project, we need to think about the equivalent civilizational-scale effort for the other core ingredient: data. At the foundation of the scaling revolution is a simple empirical law: deep neural networks improve smoothly, near magically, as you scale two things in proportion — (1) the size of the model and (2) the amount of data you train on. And despite the scaling laws being brutally diminishing, we’ve successfully bitten the bullet of logarithmic scaling with exponentially larger clusters and datasets, and received incredible new capabilities in return. But this exponential scaling is bound to hit some limits. Oddly enough, compute has compounded fairly smoothly without limit, with trillions flowing into hypercluster buildout. Instead, we’re starting to hit the limits of an exponential demand for data. Gone are the days of being purely in the compute-limited regime, where we had effectively infinite internet data but never enough GPUs, we’re now entering a data-limited regime. Luckily, this limitation is coinciding with staggering improvements in AI capabilities. Incredibly, we seem to have a real line of sight towards automating a majority of knowledge work with the methods we have today. RL + pretraining, and the data for each, will be generally sufficient to achieve most economically valuable tasks, given some minimal algorithmic progress and continued compute scaling. In a data-limited world, economic progress & scientific acceleration will be directly bottlenecked by...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# X Post by Sean Cai

> 📅 **Published:** Tue Jul 07  |  🔗 **Source:** [Sean Cai](https://x.com/i/status/2074561825157562439)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

Seems data is going mainstream again. To parrot a few points from my upcoming (sorry, delayed!) state of data june: Benchmarks/evals/rl data increasingly sourced from app layer companies and non pure play data cos - rl env companies account for a minority of how envs constructed today. Enterprise revenues by data cos quickly catching up to data revenues. Interplays where the ai transformation is subsidized by the data play becoming empirical. The best data doesn't come from data companies, but just applied AI. Similarly, the need to figure out how to unlock real world process data (besides just experts) even greater than before.

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# https://z.ai/blog/glm-5.2

> 📅 **Added:** 2026-07-13  |  🔗 **Source:** [web](https://z.ai/blog/glm-5.2)

## Summary Unavailable

Source content unavailable. The raw text fetched by the scraper was empty or insufficient, so no summary could be generated.

***

# The Art of Scaling Reinforcement Learning for LLMs | Sean Bell, Resolve AI Labs

> 📅 **Added:** 2026-07-13  |  🔗 **YouTube:** [Resolve AI - AI for Prod](https://www.youtube.com/watch?v=8exKhwg8CWQ)

## Summary Unavailable

Source content unavailable. The raw text fetched by the scraper was empty or insufficient, so no summary could be generated.

***

# victoria_lin_stanford_cs25_transformers_united_2026.pdf - Google Drive

> 📅 **Added:** 2026-07-13  |  🔗 **Source:** [web](https://drive.google.com/file/d/1zJVesVqH9R_K7Tscd5eNAQ9g38Uk_vOK/view)

## Summary Unavailable

Source content unavailable. The raw text fetched by the scraper was empty or insufficient, so no summary could be generated.

***

# Be impatient | benkuhn.net

> 📅 **Added:** 2026-07-13  |  🔗 **Source:** [web](https://www.benkuhn.net/impatient/)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

June, 2017: my partner Eve and I are stuck at the visa-on-arrival desk in the domestic transfer wing of Bole International Airport, Addis Ababa. The rest of the transfer passengers, all Ethiopian, are waltzing past us to form a monster queue at passport control. As soon as I get my precious stamp, I sprint off to hold our place before more passengers sneak in front of us. Ten minutes later, Eve finds me, groggy from our redeye and nonplussed about navigating the Ethiopian visa desk on her own. “Why did you have to run off like that?!” Somehow, “so that we could wait at the departure gate instead of in the passport control line” doesn’t seem like a very good reason. It was at this moment that I realized I was an unreasonably impatient person. (In retrospect, I probably should have been tipped off by my compulsion of doing a mental critical path analysis on any everyday activity taking more than 15 seconds, but I just thought that was normal until I started dating people and noticed they often did things in a sub-optimal order.) Now that I’ve confessed to the sin of impatience, I’m going to spend the rest of this post trying to convince you that it’s actually a good thing. (The good part is the habit of frequently asking yourself “how could this thing take less calendar time.” I don’t recommend manifesting it in annoying ways like ditching your partner in an Ethiopian airport.) Being impatient is...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***

# https://cameronrwolfe.substack.com/p/agentic-rl

> 📅 **Added:** 2026-07-13  |  🔗 **Source:** [web](https://cameronrwolfe.substack.com/p/agentic-rl)

## Summary Unavailable

Source content unavailable. The raw text fetched by the scraper was empty or insufficient, so no summary could be generated.

***

# Hot takes on AI memory

> 📅 **Published:** Sat Jul 11  |  🔗 **Source:** [Sam Z Liu](https://x.com/i/status/2075737137341940098)

## One-Paragraph Summary

Rate limit issue: The Gemini API quota was exceeded.

## Content Excerpt

One of the beautiful things about building in a new space is that there are no right answers yet. This also means that to build anything inherently involves making bets on where the ecosystem will evolve. We've compiled a (non-exhaustive) list below of questions that we discuss often with those in this space along our predictions on what the answer is. We would love to hear your thoughts, predictions, and disagreements! Is there room for memory and knowledge base companies beyond the labs? - Prediction: Companies doing vertical memory scaling (i.e. helping agents run for longer) will have a hard time competing and will be squeezed by the labs and other agentic harnesses. Companies doing horizontal scaling (i.e. across teams or entire organizations) will find a better landscape. This is because enterprise deal cycles take longer and the problems (data isolation, security, company ontology) cannot be solved by the newest model update or research idea. Should memory layers operate in weight vs token space? - Token space has a lot of advantages. It's interpretable. It's model-agnostic. It's cheap. We have decades of infrastructure built to handle storage, data isolation, modularity, etc. - Weight however seems to be more expressive and there may be a class of problems that we cannot solve purely in token space. In particular, procedural memory involving fuzzy lines and complex branching paths do not seem well suited for token space (e.g. think of trying to read the rules to a board game vs being shown how...

## Reading Priority

Low – Mostly contextual, repetitive, or niche relative to the rest of the reading queue.

***
