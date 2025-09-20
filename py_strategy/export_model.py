import torch
import torch.nn as nn
import torch.onnx

# 一个最小的 LSTM
class TinyLSTM(nn.Module):
    def __init__(self, input_dim=4, hidden_dim=2, num_layers=1):
        super(TinyLSTM, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)

    def forward(self, x):
        output, (h_n, c_n) = self.lstm(x)
        return h_n.squeeze(0)  # shape: [batch, hidden_dim]

# 实例化
model = TinyLSTM()

# 假输入 (batch=1, seq_len=3, input_dim=4)
dummy_input = torch.randn(1, 3, 4)

# 导出 ONNX
torch.onnx.export(
    model, 
    dummy_input, 
    "lstm_toy.onnx",
    input_names=["input"],
    output_names=["output"],
    dynamic_axes={"input": {0: "batch_size", 1: "seq_len"}}, 
    opset_version=11
)

print("✅ Exported lstm_toy.onnx")
