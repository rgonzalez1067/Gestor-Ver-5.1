import { useRef, useEffect, useState } from 'react';

// Contenedor con barra de scroll horizontal superior sincronizada con la inferior.
export const DualScrollX = ({ children, className = '' }) => {
  const topRef = useRef(null);
  const bodyRef = useRef(null);
  const syncing = useRef(false);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return undefined;
    const update = () => setWidth(el.scrollWidth);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    if (el.firstElementChild) ro.observe(el.firstElementChild);
    return () => ro.disconnect();
  }, []);
  const sync = (from, to) => () => {
    if (syncing.current) { syncing.current = false; return; }
    syncing.current = true;
    to.current.scrollLeft = from.current.scrollLeft;
  };
  return (
    <div className={className}>
      <div ref={topRef} onScroll={sync(topRef, bodyRef)} className="overflow-x-auto overflow-y-hidden h-3.5 border-b border-slate-100" data-testid="grid-top-scrollbar">
        <div style={{ width, height: 1 }} />
      </div>
      <div ref={bodyRef} onScroll={sync(bodyRef, topRef)} className="overflow-x-auto" data-testid="grid-body-scroll">
        {children}
      </div>
    </div>
  );
};
