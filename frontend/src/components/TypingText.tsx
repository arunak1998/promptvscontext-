import { useEffect, useState } from "react";
import { useReducedMotion } from "framer-motion";

interface Props {
  text: string;
  animate: boolean;
  onDone: () => void;
  msPerChar?: number;
}

/** Types `text` out character by character. Shows it instantly when `animate` is false or motion is reduced. */
export function TypingText({ text, animate, onDone, msPerChar = 16 }: Props) {
  const reduced = useReducedMotion();
  const instant = !animate || reduced;
  const [count, setCount] = useState(instant ? text.length : 0);

  useEffect(() => {
    if (instant) {
      setCount(text.length);
      onDone();
      return;
    }
    setCount(0);
    const id = window.setInterval(() => {
      setCount((c) => {
        if (c + 2 >= text.length) {
          window.clearInterval(id);
          onDone();
          return text.length;
        }
        return c + 2;
      });
    }, msPerChar * 2);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, instant]);

  const typing = count < text.length;
  return (
    <>
      <span aria-hidden="true">
        {text.slice(0, count)}
        {typing && <i className="caret" />}
      </span>
      <span className="sr-only" aria-live="polite">
        {typing ? "" : text}
      </span>
    </>
  );
}
