"use client";
import { KeyboardEvent, useEffect, useRef, useState } from "react";
import * as I from "./Icons";

interface Props {
  placeholder: string;
  disabled: boolean;
  onSend: (text: string) => void;
  onAttach?: (file: File) => void;
  attachLabel?: string;
  draft?: string;
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function speechCtor(): any {
  if (typeof window === "undefined") return null;
  return (window as any).SpeechRecognition ?? (window as any).webkitSpeechRecognition ?? null;
}

export default function Composer({ placeholder, disabled, onSend, onAttach, attachLabel, draft }: Props) {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const [canDictate, setCanDictate] = useState(false);
  const ta = useRef<HTMLTextAreaElement>(null);
  const file = useRef<HTMLInputElement>(null);
  const rec = useRef<any>(null);

  useEffect(() => setCanDictate(!!speechCtor()), []);
  useEffect(() => { if (draft) setText(draft); }, [draft]);
  useEffect(() => {
    const el = ta.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [text]);

  function submit() {
    const t = text.trim();
    if (!t || disabled) return;
    onSend(t);
    setText("");
  }

  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  function dictate() {
    if (listening) {
      rec.current?.stop();
      return;
    }
    const Ctor = speechCtor();
    if (!Ctor) return;
    const r = new Ctor();
    r.lang = "fr-FR";
    r.interimResults = true;
    r.continuous = false;
    const base = text ? text.replace(/\s*$/, " ") : "";
    r.onresult = (ev: any) => {
      let said = "";
      for (let i = 0; i < ev.results.length; i++) said += ev.results[i][0].transcript;
      setText(base + said);
    };
    r.onend = () => setListening(false);
    r.onerror = () => setListening(false);
    rec.current = r;
    setListening(true);
    r.start();
  }

  return (
    <div className="composer-wrap">
      <div className="composer glass">
        <button type="button" className="circle" aria-label={attachLabel ?? "Joindre un fichier"}
                title={onAttach ? attachLabel : "Pièces jointes : bientôt disponible"}
                disabled={!onAttach || disabled} onClick={() => file.current?.click()}>
          <I.Plus />
        </button>
        {onAttach && (
          <input ref={file} type="file" className="sr-only" accept=".pdf,.docx,.txt" tabIndex={-1}
                 onChange={(e) => { const f = e.target.files?.[0]; if (f) onAttach(f); e.target.value = ""; }} />
        )}
        <label htmlFor="composer" className="sr-only">Message</label>
        <textarea id="composer" ref={ta} rows={1} value={text} placeholder={placeholder}
                  onChange={(e) => setText(e.target.value)} onKeyDown={onKey} />
        {canDictate && (
          <button type="button" className={`circle ghost${listening ? " listening" : ""}`} onClick={dictate}
                  aria-label={listening ? "Arrêter la dictée" : "Dicter un message"} aria-pressed={listening}>
            <I.Mic />
          </button>
        )}
        <button type="button" className="circle send" onClick={submit} disabled={disabled || !text.trim()}
                aria-label="Envoyer">
          <I.Send />
        </button>
      </div>
    </div>
  );
}
