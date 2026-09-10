#include "Chapter/V03/ALMNSYAnimV03.h"
#include "Chapter/V03/ALMNSYFighterV03.h"
#include "Chapter/V03/SwordMotionV03.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimNode_SequencePlayer.h"
#include "Animation/AnimSequence.h"
#include "Animation/BlendSpace.h"
#include "AnimNodes/AnimNode_BlendSpacePlayer.h"
#include "BoneContainer.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
    struct FActionPlayer : FAnimNode_SequencePlayer_Standalone
    {
        using FAnimNode_SequencePlayer_Standalone::SetSequence;
        using FAnimNode_SequencePlayer_Standalone::SetPlayRate;
        using FAnimNode_SequencePlayer_Standalone::SetLoopAnimation;
        using FAnimNode_SequencePlayer_Standalone::SetStartPosition;
    };

    struct FALMNSYAnimProxy : FAnimInstanceProxy
    {
        FAnimNode_BlendSpacePlayer_Standalone MoveNode;
        FActionPlayer ActionNode;
        UBlendSpace* MovementAsset=nullptr;
        UAnimSequence* ActionAsset=nullptr;
        bool bActionChanged=false,bLoopAction=false,bWasHit=false;
        bool bDead=false,bArmed=false,bAttack=false,bGuard=false,bDodge=false;
        float Speed=0,Direction=0,Phase=0,DodgePhase=0,ActionAlpha=0,ArmAlpha=0,Scale=1;
        float TargetActionAlpha=0,Torso=0,DodgeWeight=0;
        int32 Combo=0;
        FVector Hand=FVector(27,32,116),Blade=FVector(.3,.68,.65),DodgeDirection=FVector::ZeroVector;
        FName Upper,Lower,Wrist,Spine,Pelvis,Legs[6];
        TArray<FTransform> PreviousPose,TransitionPose;
        float TransitionRemaining=0;
        bool bCaptureTransition=false;

        explicit FALMNSYAnimProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance){}
        virtual void Initialize(UAnimInstance* Instance) override
        {
            FAnimInstanceProxy::Initialize(Instance);
            MoveNode.SetLoop(true);MoveNode.SetPlayRate(1);
            ActionNode.SetLoopAnimation(false);ActionNode.SetPlayRate(1);
            const FAnimationInitializeContext Context(this);
            MoveNode.Initialize_AnyThread(Context);ActionNode.Initialize_AnyThread(Context);
        }
        virtual void PreUpdate(UAnimInstance* Instance,float Dt) override
        {
            FAnimInstanceProxy::PreUpdate(Instance,Dt);
            auto* P=Cast<AALMNSYFighterV03>(Instance->TryGetPawnOwner());if(!P)return;
            MovementAsset=P->Locomotion;
            const FVector LocalVelocity=P->GetActorTransform().InverseTransformVectorNoScale(P->GetVelocity());
            Speed=FMath::FInterpTo(Speed,P->GetVelocity().Size2D(),Dt,12);
            Direction=FMath::RadiansToDegrees(FMath::Atan2(LocalVelocity.Y,LocalVelocity.X));
            if(Speed<5)Direction=0;
            if(P->bDodging)
            {
                Speed=FMath::FInterpTo(Speed,400.f,Dt,16);
                Direction=FMath::RadiansToDegrees(FMath::Atan2(P->DodgeLocalDirection.Y,P->DodgeLocalDirection.X));
            }
            bDead=P->bDead;bArmed=P->bArmed;bAttack=P->bAttacking;bGuard=P->bGuarding;bDodge=P->bDodging;
            Phase=P->AttackPhase;DodgePhase=P->DodgePhase;Combo=P->ComboIndex;Scale=P->PoseScale;
            DodgeDirection=P->DodgeLocalDirection;
            Upper=P->RightUpperArm;Lower=P->RightForearm;Wrist=P->RightHand;Spine=P->Spine;Pelvis=P->Pelvis;
            Legs[0]=P->LeftThigh;Legs[1]=P->LeftCalf;Legs[2]=P->LeftFoot;
            Legs[3]=P->RightThigh;Legs[4]=P->RightCalf;Legs[5]=P->RightFoot;
            UAnimSequence* Desired=bDead?P->DeathAnimation.Get():P->bHitReacting?P->HitAnimation.Get():
                P->GetCharacterMovement()->IsFalling()?P->FallAnimation.Get():nullptr;
            bActionChanged=Desired && (Desired!=ActionAsset || (P->bHitReacting && !bWasHit));
            bWasHit=P->bHitReacting;
            if(Desired)ActionAsset=Desired; // retain outgoing sequence while alpha fades
            TargetActionAlpha=Desired?1.f:0.f;
            bLoopAction=!bDead && !P->bHitReacting;
        }
        virtual void CacheBones() override
        {
            const FAnimationCacheBonesContext Context(this);
            MoveNode.CacheBones_AnyThread(Context);ActionNode.CacheBones_AnyThread(Context);
        }
        virtual void Update(float Dt) override
        {
            MoveNode.SetBlendSpace(MovementAsset);
            FVector Input=FVector::ZeroVector;
            if(MovementAsset)
                for(int32 I=0;I<3;++I)
                {
                    const auto& Name=MovementAsset->GetBlendParameter(I).DisplayName;
                    if(Name.Contains(TEXT("Speed")))Input[I]=Speed;
                    else if(Name.Contains(TEXT("Direction")))Input[I]=Direction;
                }
            MoveNode.SetPosition(Input);
            if(bActionChanged)
            {
                bCaptureTransition=true;TransitionRemaining=.12f;
                ActionNode.SetSequence(ActionAsset);ActionNode.SetStartPosition(0);
                ActionNode.Initialize_AnyThread(FAnimationInitializeContext(this));bActionChanged=false;
            }
            else TransitionRemaining=FMath::Max(0.f,TransitionRemaining-Dt);
            ActionNode.SetLoopAnimation(bLoopAction);
            ActionAlpha=FMath::FInterpTo(ActionAlpha,TargetActionAlpha,Dt,bDead?16.f:20.f);
            ArmAlpha=FMath::FInterpTo(ArmAlpha,bArmed && !bDead && TargetActionAlpha<.5f?1.f:0.f,Dt,18.f);
            DodgeWeight=FMath::FInterpTo(DodgeWeight,bDodge?FMath::Sin(DodgePhase*PI):0.f,Dt,22.f);
            const auto Pose=bAttack?ALMNSYV03::SwingPose(Combo,Phase):bGuard?ALMNSYV03::GuardPose():ALMNSYV03::ReadyPose();
            // Short continuous blending applies to combo changes and attack->guard/dodge.
            Hand=FMath::VInterpTo(Hand,FVector(Pose.Hand.X,Pose.Hand.Y,Pose.Hand.Z)*Scale,Dt,32.f);
            Blade=FMath::VInterpTo(Blade,FVector(Pose.Blade.X,Pose.Blade.Y,Pose.Blade.Z),Dt,32.f).GetSafeNormal();
            Torso=FMath::FInterpTo(Torso,Pose.Torso,Dt,22.f);
            
        }
        virtual void UpdateAnimationNode(const FAnimationUpdateContext& Context) override
        {
            MoveNode.Update_AnyThread(Context);

            if (ActionAsset && ActionAlpha > .001f)
            {
                ActionNode.Update_AnyThread(Context);
            }
        }
        virtual bool Evaluate(FPoseContext& Output) override
        {
            MoveNode.Evaluate_AnyThread(Output);
            if(ActionAsset && ActionAlpha>.001f)
            {
                FPoseContext Action(this);ActionNode.Evaluate_AnyThread(Action);
                for(auto I:Output.Pose.ForEachBoneIndex())
                { FTransform Blended;Blended.Blend(Output.Pose[I],Action.Pose[I],ActionAlpha);Output.Pose[I]=Blended; }
            }
            if(bCaptureTransition)
            { TransitionPose=PreviousPose;bCaptureTransition=false; }
            if(TransitionRemaining>0 && TransitionPose.Num()==Output.Pose.GetNumBones())
                for(auto I:Output.Pose.ForEachBoneIndex())
                { FTransform Blend;Blend.Blend(Output.Pose[I],TransitionPose[I.GetInt()],TransitionRemaining/.12f);Output.Pose[I]=Blend; }
            PreviousPose.SetNum(Output.Pose.GetNumBones());
            for(auto I:Output.Pose.ForEachBoneIndex())PreviousPose[I.GetInt()]=Output.Pose[I];
            const auto& Bones=Output.Pose.GetBoneContainer();
            auto Index=[&](FName Name)
            {
                const int32 MeshIndex=Bones.GetReferenceSkeleton().FindBoneIndex(Name);
                return MeshIndex==INDEX_NONE?FCompactPoseBoneIndex(INDEX_NONE):Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(MeshIndex));
            };
            const auto Hip=Index(Pelvis),Back=Index(Spine);
            auto ComponentPose=[&]()
            {
                TArray<FTransform> Result;Result.SetNum(Output.Pose.GetNumBones());
                for(auto I:Output.Pose.ForEachBoneIndex())
                {
                    const auto Parent=Output.Pose.GetParentBoneIndex(I);
                    Result[I.GetInt()]=Parent.GetInt()==INDEX_NONE?Output.Pose[I]:Output.Pose[I]*Result[Parent.GetInt()];
                }
                return Result;
            };
            const auto BeforeCrouch=ComponentPose();
            if(Hip.GetInt()!=INDEX_NONE && !bDead)
                Output.Pose[Hip].AddToTranslation(FVector(0,0,-26*Scale*DodgeWeight));
            if(Back.GetInt()!=INDEX_NONE && !bDead)
            {
                const FQuat Lean=FRotator(DodgeDirection.X*24*DodgeWeight,Torso*ArmAlpha,-DodgeDirection.Y*20*DodgeWeight).Quaternion();
                Output.Pose[Back].SetRotation((Output.Pose[Back].GetRotation()*Lean).GetNormalized());
            }
            // Lower hips into a visible quickstep while solving both legs back to
            // the animated foot positions. The feet no longer sink with the pelvis.
            if(DodgeWeight>.001f && !bDead)
                for(int32 Side=0;Side<2;++Side)
                {
                    const auto T=Index(Legs[Side*3]),C=Index(Legs[Side*3+1]),F=Index(Legs[Side*3+2]);
                    if(T.GetInt()==INDEX_NONE || C.GetInt()==INDEX_NONE || F.GetInt()==INDEX_NONE)continue;
                    const auto LegCS=ComponentPose();
                    const FVector Origin=LegCS[T.GetInt()].GetLocation(),Knee=LegCS[C.GetInt()].GetLocation(),Foot=LegCS[F.GetInt()].GetLocation();
                    FVector Goal=BeforeCrouch[F.GetInt()].GetLocation();
                    const float A=FVector::Distance(Origin,Knee),B=FVector::Distance(Knee,Foot);
                    if(A<1 || B<1)continue;
                    const FVector Axis=(Goal-Origin).GetSafeNormal();
                    const float D=FMath::Clamp(FVector::Distance(Goal,Origin),FMath::Abs(A-B)+.1f,A+B-.1f);
                    Goal=Origin+Axis*D;
                    FVector Pole=(FVector(0,1,0)-Axis*Axis.Y).GetSafeNormal();
                    const float Along=(A*A-B*B+D*D)/(2*D);
                    const FVector Bent=Origin+Axis*Along+Pole*FMath::Sqrt(FMath::Max(0.f,A*A-Along*Along));
                    const FQuat TQ=(FQuat::FindBetweenNormals((Knee-Origin).GetSafeNormal(),(Bent-Origin).GetSafeNormal())*LegCS[T.GetInt()].GetRotation()).GetNormalized();
                    const FQuat CQ=(FQuat::FindBetweenNormals((Foot-Knee).GetSafeNormal(),(Goal-Bent).GetSafeNormal())*LegCS[C.GetInt()].GetRotation()).GetNormalized();
                    const auto Parent=Output.Pose.GetParentBoneIndex(T);
                    const FQuat PQ=Parent.GetInt()==INDEX_NONE?FQuat::Identity:LegCS[Parent.GetInt()].GetRotation();
                    Output.Pose[T].SetRotation((PQ.Inverse()*TQ).GetNormalized());
                    Output.Pose[C].SetRotation((TQ.Inverse()*CQ).GetNormalized());
                    Output.Pose[F].SetRotation((CQ.Inverse()*BeforeCrouch[F.GetInt()].GetRotation()).GetNormalized());
                }
            if(ArmAlpha<.001f)return true;
            const auto U=Index(Upper),L=Index(Lower),H=Index(Wrist);
            if(U.GetInt()==INDEX_NONE || L.GetInt()==INDEX_NONE || H.GetInt()==INDEX_NONE)return true;
            // FK snapshot. All bone lookups use the current skeleton, not Manny indices.
            TArray<FTransform> CS;CS.SetNum(Output.Pose.GetNumBones());
            for(auto I:Output.Pose.ForEachBoneIndex())
            {
                const auto Parent=Output.Pose.GetParentBoneIndex(I);
                CS[I.GetInt()]=Parent.GetInt()==INDEX_NONE?Output.Pose[I]:Output.Pose[I]*CS[Parent.GetInt()];
            }
            const FVector Shoulder=CS[U.GetInt()].GetLocation(),Elbow=CS[L.GetInt()].GetLocation(),WristPos=CS[H.GetInt()].GetLocation();
            const float A=FVector::Distance(Shoulder,Elbow),B=FVector::Distance(Elbow,WristPos);
            FVector Target=Hand+FVector(0,0,-18*Scale*DodgeWeight);
            const FVector Axis=(Target-Shoulder).GetSafeNormal();
            const float Distance=FMath::Clamp(FVector::Distance(Target,Shoulder),FMath::Abs(A-B)+.1f,A+B-.1f);
            if(A<1 || B<1 || Axis.IsNearlyZero())return true;
            Target=Shoulder+Axis*Distance;
            const float Along=(A*A-B*B+Distance*Distance)/(2*Distance);
            FVector Pole=FVector(1,0,-.28f);Pole=(Pole-Axis*FVector::DotProduct(Pole,Axis)).GetSafeNormal();
            if(Pole.IsNearlyZero())Pole=FVector(0,-1,0);
            const FVector Bent=Shoulder+Axis*Along+Pole*FMath::Sqrt(FMath::Max(0.f,A*A-Along*Along));
            const FQuat UpperCS=(FQuat::FindBetweenNormals((Elbow-Shoulder).GetSafeNormal(),(Bent-Shoulder).GetSafeNormal())*CS[U.GetInt()].GetRotation()).GetNormalized();
            const FQuat LowerCS=(FQuat::FindBetweenNormals((WristPos-Elbow).GetSafeNormal(),(Target-Bent).GetSafeNormal())*CS[L.GetInt()].GetRotation()).GetNormalized();
            const auto Parent=Output.Pose.GetParentBoneIndex(U);
            const FQuat ParentCS=Parent.GetInt()==INDEX_NONE?FQuat::Identity:CS[Parent.GetInt()].GetRotation();
            auto Rotate=[&](FCompactPoseBoneIndex I,const FQuat& Q)
            { Output.Pose[I].SetRotation(FQuat::Slerp(Output.Pose[I].GetRotation(),Q,ArmAlpha).GetNormalized()); };
            Rotate(U,ParentCS.Inverse()*UpperCS);Rotate(L,UpperCS.Inverse()*LowerCS);
            Rotate(H,LowerCS.Inverse()*FRotationMatrix::MakeFromZ(Blade).ToQuat());
            return true;
        }
    };
}
FAnimInstanceProxy* UALMNSYAnimV03::CreateAnimInstanceProxy() {return new FALMNSYAnimProxy(this);}
void UALMNSYAnimV03::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) {delete Proxy;}
