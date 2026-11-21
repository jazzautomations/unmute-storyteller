"use client";

import Image from "next/image";

import type { AgentVisualizerState } from "agora-agent-uikit";

type NovaAvatarProps = {
	state: AgentVisualizerState;
};

const STATE_LABEL: Record<AgentVisualizerState | string, string> = {
	talking: "falando",
	listening: "ouvindo você",
	analyzing: "pensando",
	ambient: "com você",
	"not-joined": "conectando",
	joining: "conectando",
	disconnected: "desconectada",
};

export function NovaAvatar({ state }: NovaAvatarProps) {
	const talking = state === "talking";
	const label = STATE_LABEL[state] ?? "com você";

	return (
		<div className="flex flex-col items-center gap-5">
			<div
				className={`relative rounded-full p-1 transition-all duration-500 ${
					talking
						? "shadow-[0_0_60px_rgba(236,72,153,0.45)] ring-4 ring-pink-500/70"
						: "shadow-[0_0_30px_rgba(255,255,255,0.08)] ring-2 ring-white/15"
				}`}
			>
				<div
					className={`relative h-56 w-56 overflow-hidden rounded-full md:h-72 md:w-72 ${
						talking ? "animate-nova-talk" : "animate-nova-breathe"
					}`}
				>
					<Image
						src="/nova.png"
						alt="Nova, entrevistadora virtual"
						fill
						priority
						className="object-cover"
						sizes="(max-width: 768px) 224px, 288px"
					/>
				</div>
				{talking ? (
					<span className="absolute inset-0 animate-ping rounded-full border-2 border-pink-500/40" />
				) : null}
			</div>
			<div className="flex items-center gap-2 text-sm text-muted-foreground">
				<span
					className={`inline-block h-2 w-2 rounded-full ${
						talking
							? "animate-pulse bg-pink-500"
							: state === "listening"
								? "animate-pulse bg-emerald-400"
								: "bg-white/30"
					}`}
				/>
				<span className="font-medium text-white/80">Nova</span>
				<span>·</span>
				<span>{label}</span>
			</div>
		</div>
	);
}
