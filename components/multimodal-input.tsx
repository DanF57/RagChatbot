"use client";

import type { ChatRequestOptions, CreateMessage, Message } from "ai";
import { motion } from "framer-motion";
import type React from "react";
import {
  useRef,
  useEffect,
  useCallback,
  type Dispatch,
  type SetStateAction,
} from "react";
import { toast } from "sonner";
import { useLocalStorage, useWindowSize } from "usehooks-ts";

import { cn, sanitizeUIMessages } from "@/lib/utils";

import { ArrowUpIcon, StopIcon, CameraIcon } from "./icons";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";

const suggestedActions = [
  {
    title: "Qué es la diabetes",
    label: "Mellitus tipo 2?",
    action: "Qué es la diabetes mellitus tipo 2?",
  },
  {
    title: "Dime 3 factores de riesgo",
    label: "para contraer diabetes",
    action: "Dime 3 factores de riesgo para contraer diabetes",
  },
];

export function MultimodalInput({
  chatId,
  input,
  setInput,
  isLoading,
  stop,
  messages,
  setMessages,
  append,
  handleSubmit,
  className,
}: {
  chatId: string;
  input: string;
  setInput: (value: string) => void;
  isLoading: boolean;
  stop: () => void;
  messages: Array<Message>;
  setMessages: Dispatch<SetStateAction<Array<Message>>>;
  append: (
    message: Message | CreateMessage,
    chatRequestOptions?: ChatRequestOptions,
  ) => Promise<string | null | undefined>;
  handleSubmit: (
    event?: {
      preventDefault?: () => void;
    },
    chatRequestOptions?: ChatRequestOptions,
  ) => void;
  className?: string;
}) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { width } = useWindowSize();

  useEffect(() => {
    if (textareaRef.current) {
      adjustHeight();
    }
  }, []);

  const adjustHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight + 2}px`;
    }
  };

  const [localStorageInput, setLocalStorageInput] = useLocalStorage(
    "input",
    "",
  );

  useEffect(() => {
    if (textareaRef.current) {
      const domValue = textareaRef.current.value;
      const finalValue = domValue || localStorageInput || "";
      setInput(finalValue);
      adjustHeight();
    }
  }, []); // Solo ejecuta en el montaje

  useEffect(() => {
    setLocalStorageInput(input);
  }, [input, setLocalStorageInput]);

  const handleInput = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(event.target.value);
    adjustHeight();
  };

  const submitForm = useCallback(() => {
    handleSubmit(undefined, {});
    setLocalStorageInput("");

    if (width && width > 768) {
      textareaRef.current?.focus();
    }
  }, [handleSubmit, setLocalStorageInput, width]);

  const speaktext = async (event: React.MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    const lastMessage = messages[messages.length - 1];
    if (lastMessage && lastMessage.role === "assistant") {
      const utterance = new SpeechSynthesisUtterance(lastMessage.content);
      utterance.lang = "es-ES";
      utterance.rate = 1;
      utterance.volume = 1;
      speechSynthesis.speak(utterance);
    } else {
      toast.error("No hay un mensaje de respuesta para leer.");
    }
  };

  return (
    <div className="relative w-full flex flex-col gap-4">
      {messages.length === 0 && (
        <div className="grid sm:grid-cols-2 gap-2 w-full">
          {suggestedActions.map((suggestedAction, index) => (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              transition={{ delay: 0.05 * index }}
              key={`suggested-action-${suggestedAction.title}-${index}`}
              className={index > 1 ? "hidden sm:block" : "block"}
            >
              <Button
                variant="ghost"
                onClick={async () => {
                  append({
                    role: "user",
                    content: suggestedAction.action,
                  });
                }}
                className="text-left border rounded-xl px-4 py-3.5 text-sm flex-1 gap-1 sm:flex-col w-full h-auto justify-start items-start"
              >
                <span className="font-medium">{suggestedAction.title}</span>
                <span className="text-muted-foreground">
                  {suggestedAction.label}
                </span>
              </Button>
            </motion.div>
          ))}
        </div>
      )}

      <Textarea
        ref={textareaRef}
        placeholder="Send a message..."
        value={input}
        onChange={handleInput}
        className={cn(
          "min-h-[24px] max-h-[calc(75dvh)] overflow-hidden resize-none rounded-xl !text-base bg-muted",
          className
        )}
        rows={3}
        autoFocus
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();

            if (isLoading) {
              toast.error(
                "Por favor, espere a que el modelo termine su respuesta"
              );
            } else {
              submitForm();
            }
          }
        }}
      />
      {isLoading ? (
        <Button
          className="rounded-full p-1.5 h-fit absolute bottom-2 right-2 m-0.5 border dark:border-zinc-600"
          onClick={(event) => {
            event.preventDefault();
            stop();
            setMessages((messages) => sanitizeUIMessages(messages));
          }}
        >
          <StopIcon size={14} />
        </Button>
      ) : (
        <div className="flex gap-2 absolute bottom-2 right-2">
          <Button
            className="rounded-full p-1.5 h-fit m-0.5 border dark:border-zinc-600"
            onClick={(event) => {
              event.preventDefault();
              submitForm();
            }}
            disabled={input.length === 0}
          >
            <ArrowUpIcon size={14} />
          </Button>
          <Button
            id="open-camera"
            onClick={async (event) => {
              event.preventDefault();
              if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                toast.error("La cámara no está disponible en este dispositivo.");
                return;
              }

              let currentStream: MediaStream | null = null;
              let useFrontCamera = true;

              const getCameraStream = async () => {
                if (currentStream) {
                  currentStream.getTracks().forEach((track) => track.stop());
                }
                const constraints = {
                  video: {
                    facingMode: useFrontCamera ? "user" : "environment",
                  },
                };
                currentStream = await navigator.mediaDevices.getUserMedia(constraints);
                return currentStream;
              };

              // Abrir la cámara
              try {
                const stream = await getCameraStream();
                const video = document.createElement("video");
                video.srcObject = stream;
                video.play();

                // Crear un modal para previsualizar y capturar la imagen
                const modal = document.createElement("div");
                modal.className =
                  "fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50";
                modal.innerHTML = `
        <div class="relative bg-white p-4 rounded-lg">
          <video autoplay muted class="w-full h-auto mb-4 rounded-lg"></video>
          <div class="flex justify-end gap-2">
            <button class="switch-camera-btn bg-gray-500 text-white px-4 py-2 rounded-lg">Cambiar cámara</button>
            <button class="capture-btn bg-blue-500 text-white px-4 py-2 rounded-lg">Capturar</button>
            <button class="cancel-btn bg-red-500 text-white px-4 py-2 rounded-lg">Cancelar</button>
          </div>
        </div>
      `;

                document.body.appendChild(modal);
                const captureBtn = modal.querySelector(".capture-btn");
                const cancelBtn = modal.querySelector(".cancel-btn");
                const switchCameraBtn = modal.querySelector(".switch-camera-btn");
                const videoEl = modal.querySelector("video") as HTMLVideoElement;
                videoEl.srcObject = stream;

                // Cambiar entre cámaras
                switchCameraBtn?.addEventListener("click", async () => {
                  useFrontCamera = !useFrontCamera;
                  const newStream = await getCameraStream();
                  videoEl.srcObject = newStream;
                });

                // Capturar imagen y enviar al backend
                captureBtn?.addEventListener("click", async () => {
                  const canvas = document.createElement("canvas");
                  canvas.width = videoEl.videoWidth;
                  canvas.height = videoEl.videoHeight;
                  const ctx = canvas.getContext("2d");
                  ctx?.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
                  const blob = await new Promise<Blob | null>((resolve) =>
                    canvas.toBlob((b) => resolve(b))
                  );

                  if (blob) {
                    const formData = new FormData();
                    formData.append("image", blob, "captured-image.jpg");

                    const response = await fetch("/api/chat/upload-image", {
                      method: "POST",
                      body: formData,
                    });

                    const result = await response.json();
                    if (response.ok) {
                      toast.success("Imagen enviada exitosamente");
                      append({
                        role: "assistant",
                        content: result.response,
                      });
                    } else {
                      toast.error("Error al enviar la imagen.");
                    }
                  }

                  modal.remove();
                  if (currentStream) {
                    currentStream.getTracks().forEach((track) => track.stop());
                  }
                });

                // Cancelar captura
                cancelBtn?.addEventListener("click", () => {
                  modal.remove();
                  if (currentStream) {
                    currentStream.getTracks().forEach((track) => track.stop());
                  }
                });
              } catch (error) {
                toast.error("Error al acceder a la cámara.");
                console.error(error);
              }
            }}
            className="rounded-full p-1.5 h-fit border dark:border-zinc-600"
          >
            <CameraIcon />
          </Button>

          <Button
            id="read"
            onClick={(event) => {
              event.preventDefault();
              speaktext(event);
            }}
            className="rounded-full p-1.5 h-fit border dark:border-zinc-600"
          >
            Leer
          </Button>
        </div>
      )}
    </div>
  );
}
