#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "ALMNSYAnimV03.generated.h"

/** Persistent locomotion/sequence blend + an analytic sword arm layer.
 * Game-thread snapshots in proxy PreUpdate; Evaluate never reads the actor.
 */
UCLASS(Transient, Blueprintable)
class ALMNSY_LEVEL01_API UALMNSYAnimV03 : public UAnimInstance
{
    GENERATED_BODY()
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* InProxy) override;
};
