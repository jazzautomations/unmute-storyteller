"use client";

import { Clapperboard, Loader2, RotateCcw, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { type FilmJob, getFilm, startFilm } from "@/services/api";

type FilmPanelProps = {
	transcript: string;
	onClose: () => void;
};

const STATUS_LABEL: Record<FilmJob["status"], string> = {
	queued: "na fila do estúdio",
	writing: "escrevendo o roteiro",
	producing: "produzindo os shots",
	rendering: "renderizando o filme",
	ready: "filme pronto",
	error: "algo deu errado",
};

export function FilmPanel({ transcript, onClose }: FilmPanelProps) {
	const [job, setJob] = useState<FilmJob | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [kicking, setKicking] = useState(false);
	const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

	const kickOff = useCallback(async () => {
		setKicking(true);
		setError(null);
		try {
			const jobId = await startFilm(transcript);
			setJob({ id: jobId, status: "queued", title: "", video_url: null, detail: "na fila" });
		} catch (e) {
			setError(e instanceof Error ? e.message : "falha ao iniciar o filme");
		} finally {
			setKicking(false);
		}
	}, [transcript]);

	useEffect(() => {
		kickOff();
	}, [kickOff]);

	useEffect(() => {
		if (!job || job.status === "ready" || job.status === "error") return;
		pollRef.current = setInterval(async () => {
			try {
				const next = await getFilm(job.id);
				setJob(next);
			} catch {
				// transient poll failure — keep polling
			}
		}, 5000);
		return () => {
			if (pollRef.current) clearInterval(pollRef.current);
		};
	}, [job]);

	const busy = kicking || (job && job.status !== "ready" && job.status !== "error");

	return (
		<div className="flex w-full max-w-2xl flex-col items-center gap-4 rounded-2xl border border-border bg-card/60 p-6">
			<div className="flex w-full items-center justify-between">
				<h2 className="flex items-center gap-2 text-lg font-semibold">
					<Clapperboard className="h-5 w-5 text-pink-500" />
					Seu filme
				</h2>
				<Button variant="ghost" size="sm" onClick={onClose} aria-label="Fechar painel do filme">
					<X className="h-4 w-4" />
				</Button>
			</div>

			{job?.status === "ready" && job.video_url ? (
				<video
					src={job.video_url}
					controls
					autoPlay
					className="aspect-video w-full rounded-xl bg-black"
				/>
			) : (
				<div className="flex aspect-video w-full flex-col items-center justify-center gap-4 rounded-xl bg-black/60">
					{error || job?.status === "error" ? (
						<>
							<p className="text-sm text-destructive">
								{error ?? job?.detail ?? "falha na produção"}
							</p>
							<Button variant="outline" size="sm" onClick={kickOff}>
								<RotateCcw className="mr-2 h-4 w-4" />
								Tentar de novo
							</Button>
						</>
					) : (
						<>
							<Loader2 className="h-8 w-8 animate-spin text-pink-500" />
							<p className="text-sm text-muted-foreground">
								{STATUS_LABEL[job?.status ?? "queued"]}
								{job?.detail ? ` — ${job.detail}` : ""}
							</p>
							<p className="px-8 text-center text-xs text-muted-foreground/70">
								O estúdio tá escrevendo, filmando e montando — isso leva alguns
								minutos.
							</p>
						</>
					)}
				</div>
			)}

			{busy ? (
				<p className="text-xs text-muted-foreground/60">
					pode continuar conversando com a Nova enquanto isso
				</p>
			) : null}
		</div>
	);
}
