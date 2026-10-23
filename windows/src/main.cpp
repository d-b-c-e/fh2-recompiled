// Prototype: FH2 on the ShiftGlue SDK (arcanite24/shiftglue-sdk), to evaluate its Vulkan FH1 native executor on
// FH2. Not part of FH2 Recompiled; built from referencias/fh2-shiftglue.

#include "generated/default/fh2_init.h"

#include <rex/cvar.h>
#include <rex/input/input_system.h>
#include <rex/logging.h>
#include <rex/rex_app.h>
#include <rex/system.h>
#include <rex/ui/presenter.h>

#include "fh2_captura.h"
#include "fh2_device_paths.h"
#include "fh2_teste_entrada.h"

REXCVAR_DEFINE_STRING(fh2_excluded_device_paths, "", "FH2",
                      "Devices the game must not open, as exact SDL device paths separated by ';' "
                      "(write / for \\), e.g. a wheel another program drives. Empty: every device "
                      "is offered as before");

namespace fh2::toque {
void Envolver(rex::RuntimeConfig& config);
}
namespace fh2::medidor {
void Arrancar();
}
#if REX_PLATFORM_ANDROID
extern "C" void fh2_android_nucleos_grandes_aplicar();
extern "C" void fh2_android_afinidade_iniciar();
#endif

class Fh2App : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;

  static std::unique_ptr<rex::ui::WindowedApp> Create(rex::ui::WindowedAppContext& ctx) {
    return std::unique_ptr<Fh2App>(new Fh2App(ctx, "fh2", PPCImageConfig));
  }

  void OnPreSetup(rex::RuntimeConfig& config) override {
    rex::cvar::SetFlagByName("mount_cache", "true");
    fh2::teste::EnvolverEntrada(config);
    ExcludeDevicePaths(config);
#if REX_PLATFORM_ANDROID
    fh2_android_nucleos_grandes_aplicar();
    fh2::toque::Envolver(config);
#endif
  }
  void OnPostSetup() override {
    fh2::medidor::Arrancar();
#if REX_PLATFORM_ANDROID
    fh2_android_afinidade_iniciar();
#endif
    fh2::captura::Arrancar([this]() -> rex::ui::Presenter* {
      const auto* rt = runtime();
      const auto* graphics = rt ? rt->graphics_system() : nullptr;
      return graphics ? graphics->presenter() : nullptr;
    });
  }
  void OnShutdown() override { fh2::captura::Parar(); }

 private:
  // The exclusions must reach the SDL driver before the window attaches; the factory runs
  // inside Runtime::Setup, before that. Unset leaves the factory as it is.
  static void ExcludeDevicePaths(rex::RuntimeConfig& config) {
    const std::string list = REXCVAR_GET(fh2_excluded_device_paths);
    if (list.empty() || !config.input_factory) return;
    auto base = config.input_factory;
    config.input_factory = [base, list](bool tool_mode) -> std::unique_ptr<rex::system::IInputSystem> {
      auto system = base(tool_mode);
      // The default factory (ui/rex_app.cpp) returns a rex::input::InputSystem.
      if (system && !fh2::InstallExcludedPaths(*static_cast<rex::input::InputSystem*>(system.get()), list)) {
        const char* message = "fh2_excluded_device_paths is set, but the input drivers did not take it. "
                              "Input is off so the excluded devices stay closed.";
        REXLOG_ERROR("{}", message);
        rex::ShowSimpleMessageBox(rex::SimpleMessageBoxType::Error, message);
        return nullptr;
      }
      return system;
    };
  }
};

REX_DEFINE_APP(fh2, Fh2App::Create)
