"""
RBLNet: ResNet18 backbone + lesion FC + multi-head attention + classifier.
Shared between training and inference so weights load cleanly.

This file is unchanged from the original Hugging Face Space
(Bhuvi046/dr-detection) so that rbl_model.pth loads without modification.
"""
import torch.nn as nn
import torchvision.models as models


class RBLNet(nn.Module):
    def __init__(self, num_classes=5, pretrained=False):
        super().__init__()
        # pretrained=False by default so it can load without internet access.
        # During training, pass pretrained=True to get ImageNet init.
        if pretrained:
            self.backbone = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
        else:
            self.backbone = models.resnet18(weights=None)

        self.backbone.fc = nn.Identity()
        self.lesion_fc = nn.Linear(512, 256)
        self.attention = nn.MultiheadAttention(
            embed_dim=256, num_heads=4, batch_first=True
        )
        self.classifier = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_classes),
        )

    def forward(self, x):
        features = self.backbone(x)
        lesion_embed = self.lesion_fc(features).unsqueeze(1)
        reasoning_out, _ = self.attention(lesion_embed, lesion_embed, lesion_embed)
        return self.classifier(reasoning_out.squeeze(1))
