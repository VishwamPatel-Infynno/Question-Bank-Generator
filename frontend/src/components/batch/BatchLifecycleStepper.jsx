import { memo, Fragment } from 'react';
import {
  CheckCircle2,
  ChevronRight
} from 'lucide-react';
import { BATCH_LIFECYCLE_STAGES } from '../../utils';

function BatchLifecycleStepper({
  batch,
  stageInfo,
  actualTotal,
  isCompleted,
  isInProgress
}) {
  return (
    <div className="batch-lifecycle-stepper" role="region" aria-label="Batch execution lifecycle">
      {BATCH_LIFECYCLE_STAGES.map((stage, idx) => {
        const StageIcon = stage.icon;
        let stepState = 'pending';

        if (isCompleted) {
          if (stage.id === 3 && !stageInfo.hasEverRefilled) {
            stepState = 'skipped';
          } else {
            stepState = 'completed';
          }
        } else if (batch.status === 'partially_completed') {
          if (stage.id < 4) {
            stepState = 'completed';
          } else {
            stepState = 'active';
          }
        } else if (isInProgress) {
          if (stage.id < stageInfo.activeStep) {
            stepState = 'completed';
          } else if (stage.id === stageInfo.activeStep) {
            stepState = 'active';
          } else {
            stepState = 'pending';
          }
        } else {
          // stopped or failed
          if (stage.id === 1) {
            stepState = actualTotal > 0 ? 'completed' : 'pending';
          } else {
            stepState = 'pending';
          }
        }

        return (
          <Fragment key={stage.id}>
            <div className={`stepper-step ${stepState}`} title={stage.desc}>
              <div className="stepper-icon-pill">
                {stepState === 'completed' ? (
                  <CheckCircle2 size={13} />
                ) : (
                  <StageIcon size={12} />
                )}
              </div>
              <div className="stepper-content">
                <span className="stepper-title">{stage.label}</span>
                <span className="stepper-subtitle">
                  {stepState === 'completed'
                    ? 'Done'
                    : stepState === 'active'
                      ? stageInfo.stageDescription
                      : stepState === 'skipped'
                        ? 'Fulfilled (No refill needed)'
                        : stage.desc}
                </span>
              </div>
            </div>
            {idx < BATCH_LIFECYCLE_STAGES.length - 1 && (
              <ChevronRight size={14} className="stepper-arrow" />
            )}
          </Fragment>
        );
      })}
    </div>
  );
}

export default memo(BatchLifecycleStepper);
