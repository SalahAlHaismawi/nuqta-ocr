import PhotosUI
import SwiftUI

extension Color {
    static let paper = Color(red: 0.953, green: 0.937, blue: 0.902)
    static let ink = Color(red: 0.078, green: 0.078, blue: 0.078)
    static let muted = Color(red: 0.431, green: 0.412, blue: 0.373)
    static let rule = Color(red: 0.847, green: 0.824, blue: 0.773)
    static let nuqtaGreen = Color(red: 0.059, green: 0.478, blue: 0.361)
    static let greenSoft = Color(red: 0.89, green: 0.937, blue: 0.914)
}

private struct SmallCaps: View {
    let text: String
    var body: some View {
        Text(text.uppercased()).font(.custom("IBM Plex Sans", size: 11)).fontWeight(.semibold)
            .tracking(1.4).foregroundColor(.muted)
    }
}

struct ContentView: View {
    @StateObject private var r = Reader()
    @State private var photo: PhotosPickerItem?
    @State private var showCamera = false
    @State private var copied = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                header
                switch r.phase {
                case .ready: main
                default: setup
                }
                Text("Open weights · Apache-2.0 · huggingface.co/SalahALHaismawi")
                    .font(.custom("IBM Plex Sans", size: 12)).foregroundColor(.muted)
                    .frame(maxWidth: .infinity).padding(.top, 28)
            }
            .padding(.horizontal, 20).padding(.top, 8).padding(.bottom, 40)
        }
        .background(Color.paper.ignoresSafeArea())
        .onChange(of: photo) { item in
            Task {
                if let data = try? await item?.loadTransferable(type: Data.self), let img = UIImage(data: data) { r.pickPhoto(img) }
            }
        }
        .sheet(isPresented: $showCamera) { CameraPicker { r.pickPhoto($0) }.ignoresSafeArea() }
    }

    // MARK: header

    private var header: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 8) {
                Circle().fill(Color.nuqtaGreen).frame(width: 10, height: 10)
                Text("Nuqta OCR").font(.custom("IBM Plex Sans", size: 15)).fontWeight(.bold).foregroundColor(.ink)
                Spacer()
                Text("ON DEVICE · OFFLINE").font(.custom("IBM Plex Sans", size: 11)).fontWeight(.bold)
                    .tracking(1.3).foregroundColor(.nuqtaGreen)
            }
            HStack(alignment: .bottom, spacing: 8) {
                Circle().fill(Color.nuqtaGreen).frame(width: 16, height: 16).padding(.bottom, 20)
                Text("نقطة").font(.custom("Noto Naskh Arabic", size: 64)).fontWeight(.bold).foregroundColor(.ink)
            }
            .padding(.top, 22)
            Text("Arabic OCR that keeps the tashkeel.")
                .font(.custom("Source Serif 4", size: 28)).fontWeight(.semibold).foregroundColor(.ink)
            Text("Nuqta-Arabic-OCR 0.8B, running on this iPhone. Nothing leaves the device.")
                .font(.custom("IBM Plex Sans", size: 15)).foregroundColor(.muted).padding(.top, 6)
        }
    }

    // MARK: setup

    private var setup: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("ONE-TIME SETUP").font(.custom("IBM Plex Sans", size: 11)).fontWeight(.bold).tracking(1.4).foregroundColor(.nuqtaGreen)
            switch r.phase {
            case .loading:
                Text("Getting ready…").font(.custom("Source Serif 4", size: 20)).fontWeight(.semibold)
                Text("Loading Nuqta-Arabic-OCR 0.8B into memory.").font(.custom("IBM Plex Sans", size: 14)).foregroundColor(.muted)
                ProgressView().tint(.nuqtaGreen)
            case .downloading(let f):
                Text("Downloading the model…").font(.custom("Source Serif 4", size: 20)).fontWeight(.semibold)
                ProgressView(value: f).tint(.nuqtaGreen)
                Text("\(Int(f * Double(ModelStore.totalBytes)) >> 20) of \(Int(ModelStore.totalBytes) >> 20) MB")
                    .font(.custom("IBM Plex Sans", size: 12)).foregroundColor(.muted)
            case .failed(let msg):
                Text("Something went wrong").font(.custom("Source Serif 4", size: 20)).fontWeight(.semibold)
                Text(msg).font(.custom("IBM Plex Sans", size: 14)).foregroundColor(.muted)
                bigButton("Try again") { ModelStore.ready ? r.load() : r.download() }
            default:
                Text("Download the model, once.").font(.custom("Source Serif 4", size: 20)).fontWeight(.semibold)
                Text("765 MB from Hugging Face. After that, Nuqta reads pages fully offline. Wi-Fi recommended.")
                    .font(.custom("IBM Plex Sans", size: 14)).foregroundColor(.muted)
                bigButton("Download 765 MB") { r.download() }
            }
        }
        .padding(18).frame(maxWidth: .infinity, alignment: .leading)
        .background(RoundedRectangle(cornerRadius: 14).fill(Color.white))
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.rule))
        .padding(.top, 22)
    }

    // MARK: main

    private var main: some View {
        VStack(alignment: .leading, spacing: 0) {
            SmallCaps(text: "Try a page").padding(.top, 26)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 10) {
                    ForEach(Reader.samples.indices, id: \.self) { i in
                        Button { r.pickSample(i) } label: {
                            VStack(spacing: 6) {
                                if let img = Reader.sampleImage(i) {
                                    Image(uiImage: img).resizable().scaledToFill().frame(width: 84, height: 96).clipped()
                                        .clipShape(RoundedRectangle(cornerRadius: 8))
                                }
                                Text(Reader.samples[i].label).font(.custom("IBM Plex Sans", size: 12)).foregroundColor(.ink)
                            }
                            .padding(6)
                            .background(RoundedRectangle(cornerRadius: 12).fill(Color.white))
                            .overlay(RoundedRectangle(cornerRadius: 12).stroke(r.sample == i ? Color.nuqtaGreen : Color.rule, lineWidth: r.sample == i ? 2 : 1))
                        }
                    }
                }
                .padding(.vertical, 2)
            }
            .padding(.top, 8)

            HStack(spacing: 12) {
                outlineButton("Take a photo") { showCamera = true }
                PhotosPicker(selection: $photo, matching: .images) { outlineLabel("From photos") }
            }
            .padding(.top, 12)

            if let page = r.page {
                Image(uiImage: page).resizable().scaledToFit().frame(maxWidth: .infinity, maxHeight: 280)
                    .padding(10)
                    .background(RoundedRectangle(cornerRadius: 14).fill(Color.white))
                    .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.rule))
                    .padding(.top, 14)
            }

            SmallCaps(text: "Output").padding(.top, 18)
            HStack(spacing: 8) {
                ForEach(Reader.prompts.indices, id: \.self) { i in
                    Button { r.mode = i } label: {
                        Text(Reader.prompts[i].0).font(.custom("IBM Plex Sans", size: 14))
                            .padding(.horizontal, 14).padding(.vertical, 8)
                            .foregroundColor(r.mode == i ? .nuqtaGreen : .ink)
                            .background(Capsule().fill(r.mode == i ? Color.greenSoft : Color.white))
                            .overlay(Capsule().stroke(r.mode == i ? Color.nuqtaGreen : Color.rule))
                    }
                }
            }
            .padding(.top, 8)

            SmallCaps(text: "Quality").padding(.top, 14)
            Picker("Quality", selection: $r.accurate) {
                Text("Most accurate").tag(true)
                Text("Faster").tag(false)
            }
            .pickerStyle(.segmented).padding(.top, 8)

            bigButton(r.running ? "Stop" : "Read the page") { r.toggleRead() }.padding(.top, 18)

            Text(r.status).font(.custom("IBM Plex Sans", size: 13)).foregroundColor(.muted)
                .frame(maxWidth: .infinity).padding(.top, 10)

            if !r.shown.isEmpty || r.running {
                output.padding(.top, 14)
            }
        }
    }

    private var output: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                SmallCaps(text: "What Nuqta reads")
                Spacer()
                Button(copied ? "Copied" : "Copy") {
                    UIPasteboard.general.string = r.shown
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
                }
                .font(.custom("IBM Plex Sans", size: 14)).fontWeight(.bold).foregroundColor(.nuqtaGreen)
            }
            Text(r.shown)
                .font(.custom("Noto Naskh Arabic", size: r.mode == 1 ? 16 : 19))
                .lineSpacing(6)
                .foregroundColor(.ink)
                .multilineTextAlignment(.trailing)
                .frame(maxWidth: .infinity, alignment: .trailing)
                .environment(\.layoutDirection, .rightToLeft)
                .textSelection(.enabled)
            if !r.stats.isEmpty {
                Text(r.stats).font(.custom("IBM Plex Sans", size: 12)).foregroundColor(.muted)
            }
        }
        .padding(18)
        .background(RoundedRectangle(cornerRadius: 14).fill(Color.white))
        .overlay(alignment: .trailing) {
            RoundedRectangle(cornerRadius: 2).fill(Color.nuqtaGreen).frame(width: 4).padding(.vertical, 14)
        }
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.rule))
    }

    // MARK: buttons

    private func bigButton(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title).font(.custom("IBM Plex Sans", size: 17)).fontWeight(.semibold).foregroundColor(.white)
                .frame(maxWidth: .infinity).frame(height: 58)
                .background(RoundedRectangle(cornerRadius: 16).fill(Color.nuqtaGreen))
        }
    }

    private func outlineLabel(_ title: String) -> some View {
        Text(title).font(.custom("IBM Plex Sans", size: 15)).foregroundColor(.ink)
            .frame(maxWidth: .infinity).frame(height: 50)
            .background(RoundedRectangle(cornerRadius: 14).fill(Color.white))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.rule))
    }

    private func outlineButton(_ title: String, action: @escaping () -> Void) -> some View {
        Button(action: action) { outlineLabel(title) }
    }
}
