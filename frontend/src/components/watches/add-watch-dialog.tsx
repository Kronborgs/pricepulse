"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Plus, CheckCircle, Loader2, X } from "lucide-react";
import { api } from "@/lib/api";
import { getDomain } from "@/lib/utils";

const schema = z.object({
  url: z.string().url("Angiv en gyldig URL (inkl. https://)"),
  check_interval: z.coerce.number().min(5).max(10080).default(60),
});

type FormData = z.infer<typeof schema>;

export function AddWatchDialog() {
  const [open, setOpen] = useState(false);
  const [lastAdded, setLastAdded] = useState<string | null>(null);

  const qc = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { check_interval: 60 },
  });

  const createMutation = useMutation({
    mutationFn: api.watches.create,
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["watches"] });
      qc.invalidateQueries({ queryKey: ["dashboard-stats"] });
      setLastAdded(getDomain(variables.url));
      reset();
      setTimeout(() => setLastAdded(null), 4000);
    },
  });

  async function onSubmit(data: FormData) {
    createMutation.mutate({
      url: data.url,
      check_interval: data.check_interval,
      provider: "http",
    });
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        <Plus className="h-4 w-4" />
        Tilføj watch
      </button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div className="bg-card rounded-xl border border-border shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-border">
          <h2 className="text-lg font-semibold">Tilføj ny watch</h2>
          <button onClick={() => { setOpen(false); reset(); }} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="p-5 space-y-4">
          {/* Succes-besked */}
          {lastAdded && (
            <div className="flex items-center gap-2 rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 px-3 py-2 text-sm text-green-700 dark:text-green-400">
              <CheckCircle className="h-4 w-4 flex-shrink-0" />
              <span><strong>{lastAdded}</strong> tilføjet — indtast ny URL for at fortsætte</span>
            </div>
          )}

          {/* URL input */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Produkt URL</label>
            <input
              {...register("url")}
              placeholder="https://www.komplett.dk/product/..."
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            />
            {errors.url && (
              <p className="text-xs text-destructive">{errors.url.message}</p>
            )}
          </div>

          {/* Check interval */}
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Tjek-interval</label>
            <select
              {...register("check_interval")}
              className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
            >
              <option value={15}>Hver 15 minutter</option>
              <option value={30}>Hver 30 minutter</option>
              <option value={60}>Hver time</option>
              <option value={360}>Hver 6. time</option>
              <option value={720}>To gange dagligt</option>
              <option value={1440}>Dagligt</option>
            </select>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => { setOpen(false); reset(); }}
              className="rounded-md px-4 py-2 text-sm border border-border hover:bg-accent transition-colors"
            >
              Annuller
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Tilføj watch
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
