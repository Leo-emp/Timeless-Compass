// A job's film by name. Remotion serialises composition props (functions are dropped), so the composition only
// carries the job's slug and the scene functions are looked up here from the generated index.
import React from 'react';
import { JOBS } from '../jobs';
import { Film } from './Film';

export const JobFilm: React.FC<{ slug: string }> = ({ slug }) => {
  const job = JOBS.find((j) => j.slug === slug);
  if (!job) throw new Error(`no job ${slug} in film/src/jobs/index.ts (run tc filmjob build)`);
  return <Film plan={job.plan} scenes={job.scenes} />;
};
